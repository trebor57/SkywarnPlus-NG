"""
Alerts API handlers mixin.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web
from aiohttp.web import Request, Response

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AlertsApiMixin:
    async def api_alerts_handler(self, request: Request) -> Response:
        """Handle API alerts endpoint."""
        try:
            # Get current alerts from state
            active_alerts = self.app.state.get("active_alerts", [])
            alerts_data = []

            # Get monitored county codes for filtering
            monitored_county_codes = set()
            if self.app and hasattr(self.app, "config"):
                monitored_county_codes = {
                    county.code for county in self.app.config.counties if county.enabled
                }

            for alert_id in active_alerts:
                alert_data = self.app.state.get("last_alerts", {}).get(alert_id)
                if alert_data:
                    # Filter county codes to only monitored counties
                    if monitored_county_codes and "county_codes" in alert_data:
                        original_codes = alert_data.get("county_codes", [])
                        filtered_codes = [
                            code for code in original_codes if code in monitored_county_codes
                        ]

                        # If no county codes matched, try to extract from area_desc
                        if not filtered_codes and self.app and hasattr(self.app, "config"):
                            area_desc = alert_data.get("area_desc", "")
                            if area_desc:
                                # Build a map of county names (normalized) to county codes
                                county_name_to_code = {}
                                for county in self.app.config.counties:
                                    if county.enabled and county.name:
                                        # Normalize county name (remove " County" suffix, lowercase)
                                        normalized_name = (
                                            county.name.replace(" County", "")
                                            .replace(" county", "")
                                            .lower()
                                        )
                                        county_name_to_code[normalized_name] = county.code

                                        # Also add without "Island", "Islands", etc. for matching
                                        base_name = re.sub(
                                            r"\s+(island|islands|peninsula|beach|beaches)\s*$",
                                            "",
                                            normalized_name,
                                            flags=re.IGNORECASE,
                                        )
                                        if base_name != normalized_name:
                                            county_name_to_code[base_name] = county.code

                                # Parse area_desc and try to match county names
                                area_parts = [part.strip() for part in re.split(r"[;,]", area_desc)]
                                matched_codes = []
                                for area_part in area_parts:
                                    # Remove common suffixes and normalize
                                    normalized_area = (
                                        re.sub(
                                            r"\s+(island|islands|peninsula|beach|beaches|county)\s*$",
                                            "",
                                            area_part,
                                            flags=re.IGNORECASE,
                                        )
                                        .lower()
                                        .strip()
                                    )

                                    # Try exact match first
                                    if normalized_area in county_name_to_code:
                                        code = county_name_to_code[normalized_area]
                                        if code not in matched_codes:
                                            matched_codes.append(code)
                                    else:
                                        # Try partial match (e.g., "Brazoria" in "Brazoria Islands")
                                        for county_name, code in county_name_to_code.items():
                                            if (
                                                county_name in normalized_area
                                                or normalized_area in county_name
                                            ):
                                                if code not in matched_codes:
                                                    matched_codes.append(code)

                                if matched_codes:
                                    filtered_codes = matched_codes

                        if filtered_codes:
                            # Create filtered alert data
                            filtered_alert = alert_data.copy()
                            filtered_alert["county_codes"] = filtered_codes

                            # Filter area_desc if possible
                            if "area_desc" in filtered_alert and filtered_alert["area_desc"]:
                                area_desc = filtered_alert["area_desc"]
                                # Try to match county names from area_desc
                                county_code_to_name = {
                                    county.code: county.name
                                    for county in self.app.config.counties
                                    if county.enabled and county.name
                                }
                                area_parts = [part.strip() for part in re.split(r"[;,]", area_desc)]
                                filtered_parts = []

                                for part in area_parts:
                                    if not part:
                                        continue
                                    part_lower = part.lower().strip()
                                    matched = False

                                    # Check by county name
                                    for code, name in county_code_to_name.items():
                                        if name:
                                            name_lower = name.lower().strip()
                                            if (
                                                part_lower == name_lower
                                                or part_lower == name_lower.replace(" county", "")
                                                or part_lower
                                                == name_lower.replace(" county", "").replace(
                                                    " ", ""
                                                )
                                            ):
                                                filtered_parts.append(part)
                                                matched = True
                                                break

                                    # Check by county code
                                    if not matched:
                                        for code in monitored_county_codes:
                                            if code.lower() in part_lower:
                                                filtered_parts.append(part)
                                                matched = True
                                                break

                                if filtered_parts:
                                    filtered_alert["area_desc"] = "; ".join(filtered_parts)
                                elif len(filtered_codes) < len(original_codes):
                                    # Build area_desc from county names
                                    county_names = []
                                    for code in filtered_codes:
                                        if code in county_code_to_name:
                                            county_names.append(county_code_to_name[code])
                                    if county_names:
                                        filtered_alert["area_desc"] = "; ".join(county_names)

                            alerts_data.append(filtered_alert)
                        # If no monitored counties, skip this alert
                    else:
                        alerts_data.append(alert_data)

            return web.json_response(
                {
                    "alerts": alerts_data,
                    "count": len(alerts_data),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def api_alert_audio_handler(self, request: Request) -> Response:
        """Generate and stream TTS audio for a specific alert."""
        try:
            alert_id = request.match_info.get("alert_id")
            if not alert_id:
                return web.json_response({"error": "alert_id is required"}, status=400)

            # Ensure audio subsystem is available
            if not self.app or not self.app.audio_manager:
                return web.json_response({"error": "Audio system not available"}, status=503)

            # Look up alert data from state
            alert_data = self.app.state.get("last_alerts", {}).get(alert_id)
            if not alert_data:
                return web.json_response({"error": "Alert not found or expired"}, status=404)

            # Construct WeatherAlert model defensively
            try:
                from ...core.models import WeatherAlert

                alert_model = WeatherAlert(**alert_data)
            except Exception:
                # Fallback: minimal model using required fields
                from datetime import datetime
                from ...core.models import WeatherAlert

                minimal = {
                    "id": alert_data.get("id", alert_id),
                    "event": alert_data.get("event", "Weather Alert"),
                    "description": alert_data.get("description", alert_data.get("area_desc", "")),
                    "sent": datetime.now(timezone.utc),
                    "effective": datetime.now(timezone.utc),
                    "expires": datetime.now(timezone.utc),
                    "area_desc": alert_data.get("area_desc", ""),
                    "sender": alert_data.get("sender", "NWS"),
                    "sender_name": alert_data.get("sender_name", "National Weather Service"),
                }
                alert_model = WeatherAlert(**minimal)

            # Get county audio files if county names are enabled (same logic as _announce_alert)
            county_audio_files = None
            if self.app.config.alerts.with_county_names:
                county_codes_list = getattr(alert_model, "county_codes", []) or []
                area_desc = getattr(alert_model, "area_desc", None)
                if county_codes_list:
                    county_audio_files = self.app._get_county_audio_files(
                        county_codes_list, area_desc=area_desc
                    )

            # Generate audio file with county audio if enabled
            audio_path = self.app.audio_manager.generate_alert_audio(
                alert_model, county_audio_files=county_audio_files
            )
            if not audio_path or not audio_path.exists():
                return web.json_response({"error": "Failed to generate audio"}, status=500)

            # Determine content type from extension
            ext = audio_path.suffix.lower()

            # Convert ulaw to WAV for browser compatibility (browsers can't play ulaw)
            if ext in [".ulaw", ".ul"]:
                import tempfile
                import subprocess

                # Create temporary WAV file for conversion
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_wav_path = Path(temp_wav.name)

                try:
                    # Convert ulaw to WAV using ffmpeg
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-f",
                            "mulaw",  # Input format: mulaw
                            "-ar",
                            "8000",  # Sample rate: 8kHz (standard for ulaw)
                            "-ac",
                            "1",  # Channels: mono
                            "-i",
                            str(audio_path),
                            str(temp_wav_path),
                        ],
                        check=True,
                        capture_output=True,
                        timeout=30,
                        text=True,
                    )

                    # Read the converted WAV file into memory
                    wav_data = temp_wav_path.read_bytes()

                    # Clean up temp file
                    try:
                        temp_wav_path.unlink(missing_ok=True)
                    except Exception:
                        pass

                    # Return WAV data as response
                    return web.Response(body=wav_data, headers={"Content-Type": "audio/wav"})
                except subprocess.CalledProcessError as e:
                    logger.error(
                        f"Failed to convert ulaw to WAV: {e.stderr if e.stderr else 'Unknown error'}"
                    )
                    # Clean up temp file
                    try:
                        temp_wav_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    # Fallback: try to return original file anyway
                    return web.FileResponse(
                        path=str(audio_path), headers={"Content-Type": "application/octet-stream"}
                    )
                except Exception as conv_e:
                    logger.error(f"Error during ulaw conversion: {conv_e}")
                    # Clean up temp file on error
                    try:
                        temp_wav_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    # Fallback: return original file
                    return web.FileResponse(
                        path=str(audio_path), headers={"Content-Type": "application/octet-stream"}
                    )

            # Handle other formats
            if ext in [".mp3"]:
                content_type = "audio/mpeg"
            elif ext in [".wav"]:
                content_type = "audio/wav"
            elif ext in [".ogg"]:
                content_type = "audio/ogg"
            else:
                content_type = "application/octet-stream"

            # Stream file to client
            return web.FileResponse(path=str(audio_path), headers={"Content-Type": content_type})
        except Exception as e:
            logger.error(f"Error generating alert audio: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def api_alerts_history_handler(self, request: Request) -> Response:
        """Handle API alerts history endpoint."""
        try:
            if not self.app.database_manager:
                return web.json_response({"error": "Database not available"}, status=503)

            # Get query parameters
            limit = int(request.query.get("limit", 100))
            hours = int(request.query.get("hours", 24))

            # Get alerts from database
            alerts = await self.app.database_manager.get_recent_alerts(limit=limit, hours=hours)

            # Convert to dict format
            alerts_data = []
            for alert in alerts:
                # Helper function to safely format datetime
                def format_datetime(dt):
                    if dt is None:
                        return None
                    if hasattr(dt, "isoformat"):
                        return dt.isoformat()
                    # If it's already a string, return as-is
                    return str(dt)

                alerts_data.append(
                    {
                        "id": alert.id,
                        "event": alert.event,
                        "severity": alert.severity,
                        "area_desc": alert.area_desc,
                        "effective_time": format_datetime(alert.effective_time),
                        "expires_time": format_datetime(alert.expires_time),
                        "processed_at": format_datetime(alert.processed_at),
                        "announced": alert.announced,
                        "script_executed": alert.script_executed,
                    }
                )

            return web.json_response(
                {
                    "alerts": alerts_data,
                    "count": len(alerts_data),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error getting alerts history: {e}")
            return web.json_response({"error": str(e)}, status=500)
