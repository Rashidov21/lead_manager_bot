"""
Google Sheets integration module.
Handles reading and writing lead data to/from Google Sheets.
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from loguru import logger

from config import (
    GOOGLE_SHEET_ID,
    GOOGLE_SHEET_NAME,
    SERVICE_ACCOUNT_PATH,
    COLUMNS,
    MAX_RETRIES,
    RETRY_DELAY,
)
from utils.time_utils import now_utc, format_datetime, parse_datetime


class GoogleSheetsClient:
    """Client for interacting with Google Sheets."""

    def __init__(self):
        self.sheet = None
        self.worksheet = None
        self._initialized = False

    async def initialize(self):
        """Initialize Google Sheets connection."""
        if self._initialized:
            return

        try:
            # Run synchronous gspread operations in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_initialize)
            self._initialized = True
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            raise

    def _sync_initialize(self):
        """Synchronous initialization of Google Sheets."""
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            str(SERVICE_ACCOUNT_PATH), scopes=scope
        )
        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(GOOGLE_SHEET_ID)
        self.worksheet = self.sheet.worksheet(GOOGLE_SHEET_NAME)

    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry a Google Sheets operation with exponential backoff."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, operation, *args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Google Sheets operation failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Google Sheets operation failed after {MAX_RETRIES} attempts: {e}")

        raise last_error

    async def get_all_leads(self) -> List[Dict]:
        """
        Fetch all leads from the sheet.
        Returns list of dictionaries with column names as keys.
        """
        await self.initialize()

        def _fetch():
            # Get all values (skip header row)
            values = self.worksheet.get_all_values()
            if len(values) <= 1:
                return []

            headers = values[0]
            leads = []

            for row_idx, row in enumerate(values[1:], start=2):  # Start from row 2 (after header)
                if not row or not row[COLUMNS["ID"]]:  # Skip empty rows
                    continue

                lead = {}
                for col_name, col_idx in COLUMNS.items():
                    value = row[col_idx] if col_idx < len(row) else ""
                    lead[col_name] = value.strip() if value else ""

                lead["_row_number"] = row_idx  # Store row number for updates
                leads.append(lead)

            return leads

        try:
            leads = await self._retry_operation(_fetch)
            logger.debug(f"Fetched {len(leads)} leads from Google Sheets")
            return leads
        except Exception as e:
            logger.error(f"Error fetching leads: {e}")
            return []

    async def get_lead_by_id(self, lead_id: str) -> Optional[Dict]:
        """Get a specific lead by ID."""
        leads = await self.get_all_leads()
        for lead in leads:
            if lead.get("ID", "").strip() == lead_id.strip():
                return lead
        return None

    async def get_leads_by_seller(self, seller_name: str) -> List[Dict]:
        """
        Get all leads for a specific seller.
        Matches by exact case-insensitive comparison of seller name.
        """
        if not seller_name or not seller_name.strip():
            logger.warning("Empty seller_name provided to get_leads_by_seller")
            return []
        
        leads = await self.get_all_leads()
        seller_name_clean = seller_name.strip().lower()
        
        matched_leads = []
        for lead in leads:
            lead_seller = lead.get("Seller", "").strip()
            if lead_seller.lower() == seller_name_clean:
                matched_leads.append(lead)
        
        logger.debug(f"Found {len(matched_leads)} leads for seller '{seller_name}'")
        return matched_leads
    
    async def get_leads_by_seller_with_status(self, seller_name: str, status: Optional[str] = None) -> List[Dict]:
        """
        Get leads for a seller, optionally filtered by status.
        """
        leads = await self.get_leads_by_seller(seller_name)
        if status:
            status_clean = status.strip()
            leads = [lead for lead in leads if lead.get("Status", "").strip() == status_clean]
        return leads

    async def update_lead(self, lead_id: str, updates: Dict[str, str]) -> bool:
        """
        Update a lead in the sheet.
        updates: Dictionary with column names as keys and new values as values.
        """
        await self.initialize()

        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            logger.warning(f"Lead {lead_id} not found for update")
            return False

        row_number = lead.get("_row_number")
        if not row_number:
            logger.error(f"No row number found for lead {lead_id}")
            return False

        # Add Last_Update timestamp
        updates["Last_Update"] = format_datetime(now_utc())

        def _update():
            batch_updates = []
            for col_name, value in updates.items():
                if col_name not in COLUMNS:
                    logger.warning(f"Unknown column: {col_name}")
                    continue

                col_idx = COLUMNS[col_name]
                # Convert column index to letter (A=0, B=1, etc.)
                col_letter = chr(65 + col_idx) if col_idx < 26 else chr(64 + col_idx // 26) + chr(65 + col_idx % 26)
                range_name = f"{col_letter}{row_number}"
                
                batch_updates.append({
                    "range": range_name,
                    "values": [[str(value) if value else ""]]
                })

            if batch_updates:
                self.worksheet.batch_update(batch_updates)

        try:
            await self._retry_operation(_update)
            logger.info(f"Updated lead {lead_id}: {updates}")
            return True
        except Exception as e:
            logger.error(f"Error updating lead {lead_id}: {e}")
            return False

    async def update_lead_status(self, lead_id: str, new_status: str) -> bool:
        """Update lead status."""
        return await self.update_lead(lead_id, {"Status": new_status})

    async def update_call_time(self, lead_id: str, call_number: int, call_time: Optional[datetime] = None) -> bool:
        """Update call time for a lead."""
        if call_time is None:
            call_time = now_utc()

        call_column = f"Call_{call_number}_Time"
        if call_column not in COLUMNS:
            logger.error(f"Invalid call number: {call_number}")
            return False

        return await self.update_lead(lead_id, {call_column: format_datetime(call_time)})

    async def get_new_leads_since(self, since: datetime) -> List[Dict]:
        """Get leads created since a specific datetime."""
        leads = await self.get_all_leads()
        new_leads = []

        for lead in leads:
            created_at_str = lead.get("Created_At", "")
            if not created_at_str:
                continue

            created_at = parse_datetime(created_at_str)
            if created_at and created_at >= since:
                new_leads.append(lead)

        return new_leads


# Global instance
sheets_client = GoogleSheetsClient()

