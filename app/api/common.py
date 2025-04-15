import aiohttp
import asyncio
import json
import logging
from typing import Dict
from fastapi import status

logger = logging.getLogger(__name__)

API_URLS = {
    "fssp": "https://api-cloud.ru/api/fssp.php",
    "gibdd": "https://api-cloud.ru/api/gibdd.php",
    "mvd": "https://api-cloud.ru/api/mvd.php",
    "arbitr": "https://api-cloud.ru/api/ras_arbitr.php",
    "bankrot": "https://api-cloud.ru/api/bankrot.php",
    "zalog": "https://api-cloud.ru/api/zalog.php"
}

async def make_api_request(api_name: str, params: Dict) -> Dict:
    logger.debug(f"Request to {api_name}: {params}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_URLS[api_name],
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_text = await response.text()
                try:
                    response_json = json.loads(response_text)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response from {api_name}: {response_text}")
                    return {
                        "status": "error",
                        "message": "Invalid JSON response",
                        "details": response_text
                    }
                if 200 <= response.status < 300:
                    logger.debug(f"API {api_name} returned {response.status}: {response_json}")
                    return response_json
                else:
                    logger.error(f"API {api_name} returned {response.status}: {response_text}")
                    return {
                        "status": "error",
                        "message": f"API error: {response.status}",
                        "details": response_text
                    }
    except asyncio.TimeoutError:
        logger.error(f"Timeout when accessing {api_name}")
        return {
            "status": "timeout",
            "message": "Service timeout",
            "details": "Try again later"
        }
    except Exception as e:
        logger.error(f"Error accessing {api_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": "Connection error",
            "details": str(e)
        }
