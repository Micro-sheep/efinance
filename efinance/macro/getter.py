import os
from typing import Any, Dict, Optional

import pandas as pd

from ..shared import session


FXMACRODATA_BASE_URL = "https://api.fxmacrodata.com"


def _api_key(api_key: Optional[str]) -> Optional[str]:
    return api_key or os.getenv("FXMD_API_KEY") or os.getenv("FXMACRODATA_API_KEY")


def _clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            cleaned[key] = str(value).lower()
        else:
            cleaned[key] = value
    return cleaned


def _request(path: str, api_key: Optional[str] = None, **params: Any) -> Any:
    headers = {}
    key = _api_key(api_key)
    if key:
        headers["X-API-Key"] = key

    response = session.get(
        FXMACRODATA_BASE_URL + path,
        params=_clean_params(params),
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _frame(payload: Any) -> pd.DataFrame:
    if isinstance(payload, list):
        return pd.json_normalize(payload)

    if isinstance(payload, dict):
        for key in (
            "data",
            "items",
            "results",
            "records",
            "calendar",
            "announcements",
            "predictions",
            "series",
            "cot",
            "commodities",
            "sessions",
            "indicators",
            "capabilities",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                df = pd.json_normalize(value)
                for meta_key, meta_value in payload.items():
                    if meta_key == key or isinstance(meta_value, (dict, list)):
                        continue
                    if meta_key not in df.columns:
                        df[meta_key] = meta_value
                return df
        return pd.json_normalize(payload)

    return pd.DataFrame({"value": [payload]})


def get_data_catalogue(
    currency: str = "usd",
    include_capabilities: Optional[bool] = None,
    include_coverage: Optional[bool] = None,
    indicator: Optional[str] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get FXMacroData catalogue and coverage metadata.

    Parameters
    ----------
    currency : str, optional
        Three-letter currency code, such as ``"usd"``.
    include_capabilities : bool, optional
        Include endpoint capability metadata when supported by the API.
    include_coverage : bool, optional
        Include coverage metadata when supported by the API.
    indicator : str, optional
        Filter catalogue rows to one indicator.
    api_key : str, optional
        FXMacroData API key. Defaults to ``FXMD_API_KEY`` or
        ``FXMACRODATA_API_KEY`` from the environment.

    Returns
    -------
    DataFrame
        Catalogue rows returned by FXMacroData.
    """
    payload = _request(
        "/v1/data_catalogue/{currency}".format(currency=currency.lower()),
        include_capabilities=include_capabilities,
        include_coverage=include_coverage,
        indicator=indicator,
        api_key=api_key,
    )
    return _frame(payload)


def get_indicator(
    currency: str,
    indicator: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    series_mode: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    page: Optional[int] = None,
    seasonality: Optional[bool] = None,
    frequency: Optional[str] = None,
    revisions: Optional[bool] = None,
    basis: Optional[str] = None,
    official_only: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get FXMacroData macro announcement or indicator history rows.
    """
    payload = _request(
        "/v1/announcements/{currency}/{indicator}".format(
            currency=currency.lower(), indicator=indicator
        ),
        start_date=start_date,
        end_date=end_date,
        series_mode=series_mode,
        limit=limit,
        offset=offset,
        page=page,
        seasonality=seasonality,
        frequency=frequency,
        revisions=revisions,
        basis=basis,
        official_only=official_only,
        api_key=api_key,
    )
    return _frame(payload)


def get_calendar(
    currency: str = "usd",
    indicator: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timezone: Optional[str] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get FXMacroData economic release-calendar rows.
    """
    payload = _request(
        "/v1/calendar/{currency}".format(currency=currency.lower()),
        indicator=indicator,
        start_date=start_date,
        end_date=end_date,
        timezone=timezone,
        api_key=api_key,
    )
    return _frame(payload)


def get_latest_announcements(
    currency: str = "usd", api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    Get the latest FXMacroData announcements for a currency.
    """
    payload = _request(
        "/v1/announcements/{currency}/latest".format(currency=currency.lower()),
        api_key=api_key,
    )
    return _frame(payload)


def get_predictions(
    currency: str,
    indicator: str,
    prediction_type: Optional[str] = None,
    prediction_source: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    page: Optional[int] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get FXMacroData prediction, consensus, or forecast rows.
    """
    payload = _request(
        "/v1/predictions/{currency}/{indicator}".format(
            currency=currency.lower(), indicator=indicator
        ),
        prediction_type=prediction_type,
        prediction_source=prediction_source,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        page=page,
        api_key=api_key,
    )
    return _frame(payload)


def get_forex(
    base: str,
    quote: str = "usd",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    page: Optional[int] = None,
    indicators: Optional[str] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get FXMacroData FX spot history rows.
    """
    payload = _request(
        "/v1/forex/{base}/{quote}".format(base=base.lower(), quote=quote.lower()),
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        page=page,
        indicators=indicators,
        api_key=api_key,
    )
    return _frame(payload)


def get_cot(
    currency: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    page: Optional[int] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get FXMacroData COT positioning rows.
    """
    payload = _request(
        "/v1/cot/{currency}".format(currency=currency.lower()),
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        page=page,
        api_key=api_key,
    )
    return _frame(payload)


def get_commodities(
    indicator: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    page: Optional[int] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get FXMacroData commodity or energy rows.
    """
    payload = _request(
        "/v1/commodities/{indicator}".format(indicator=indicator),
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        page=page,
        api_key=api_key,
    )
    return _frame(payload)


def get_market_sessions(at: Optional[str] = None) -> pd.DataFrame:
    """
    Get FXMacroData market-session rows.
    """
    payload = _request("/v1/market_sessions", at=at)
    return _frame(payload)
