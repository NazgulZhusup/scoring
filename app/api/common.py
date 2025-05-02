# common.py

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

API_URLS = {
    "fssp": "https://api-cloud.ru/api/fssp.php",
    "gibdd": "https://api-cloud.ru/api/gibdd.php",
    "mvd": "https://api-cloud.ru/api/mvd.php",
    "arbitr": "https://api-cloud.ru/api/ras_arbitr.php",
    "bankrot": "https://api-cloud.ru/api/bankrot.php",
    "zalog": "https://api-cloud.ru/api/zalog.php"
}

TIMEOUTS = {
    "fssp": 30,
    "gibdd": 45,
    "mvd": 30,
    "arbitr": 30,
    "bankrot": 30,
    "zalog": 30
}

async def make_api_request(service_name: str, params: Dict[str, Any], max_retries: int = 2, retry_delay: float = 1.0) -> Dict[str, Any]:
    if service_name not in API_URLS:
        logger.error(f"Unknown service: {service_name}")
        return {
            "status": "error",
            "message": f"Unknown service: {service_name}",
            "details": None
        }

    url = API_URLS[service_name]
    timeout = aiohttp.ClientTimeout(total=TIMEOUTS.get(service_name, 30))
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_retries} for {service_name}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=timeout) as response:
                    response_text = await response.text()
                    try:
                        result = json.loads(response_text)
                        result["_metadata"] = {
                            "service": service_name,
                            "timestamp": datetime.now().isoformat(),
                            "attempt": attempt,
                            "status_code": response.status
                        }
                        return result
                    except json.JSONDecodeError:
                        last_error = {
                            "status": "error",
                            "message": f"Invalid JSON from {service_name}",
                            "details": response_text[:500],
                            "status_code": response.status
                        }
        except asyncio.TimeoutError:
            last_error = {
                "status": "timeout",
                "message": f"Timeout while accessing {service_name}",
                "details": f"Timeout after {timeout.total} seconds",
                "status_code": 408
            }
        except Exception as e:
            last_error = {
                "status": "error",
                "message": f"Error with {service_name}: {str(e)}",
                "details": str(e),
                "status_code": 500
            }

        if attempt < max_retries:
            await asyncio.sleep(retry_delay)

    return last_error or {
        "status": "error",
        "message": "Unknown error occurred",
        "details": None,
        "status_code": 500
    }