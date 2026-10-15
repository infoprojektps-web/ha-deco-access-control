"""Config flow for the Deco Access Control integration."""
import logging
from urllib.parse import urlsplit
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .client import DecoController
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

def normalize_host(value: str) -> str:
    raw = value.strip()
    parsed = urlsplit(raw if "://" in raw else "http://" + raw)
    if not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/"):
        raise ValueError("Invalid host")
    if parsed.port not in (None, 80, 443):
        raise ValueError("Unsupported port")
    return parsed.hostname

class DecoAccessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                host = normalize_host(user_input["host"])
                await self.async_set_unique_id(host)
                controller = DecoController(host, user_input["username"], user_input["password"])
                await self.hass.async_add_executor_job(controller.poll)
            except ValueError:
                errors["base"] = "invalid_host"
            except Exception as exc:
                _LOGGER.warning("Deco setup failed (%s)", type(exc).__name__)
                errors["base"] = "cannot_connect"
            else:
                user_input = dict(user_input)
                user_input["host"] = host
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Deco {host}", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("username", default="admin"): str,
                vol.Required("password"): str,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
                    vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
            }),
            errors=errors,
        )
