"""Unit tests for the freva databrowser module."""
import json

from fastapi.testclient import TestClient
from databrowser.core import SolrSearch


def test_databrowser(client: TestClient) -> None:
    """Test the default databrowser functionality."""
    res1 = client.get(
        "databrowser/cmip6/uri", params={"start": "f", "activity_id": "cmip"}
    )
    res2 = client.get(
        "databrowser/cmip6/uri",
        params={"translate": "false", "product": "cmip"},
    )
    res3 = client.get("databrowser/freva/uri", params={"product": "cmip"})
    assert len(res1.text.split()) > 0
    assert res1.text == res2.text == res3.text
    res3 = client.get("databrowser/freva/uri", params={"foo": "cmip"})
    assert res3.status_code == 400
    assert res3.text.split() == []


def test_time_selection(client: TestClient) -> None:
    """Test the time select functionality of the API."""
    res1 = client.get(
        "databrowser/freva/file", params={"time": "1898 to 1901"}
    )
    assert len(res1.text.split()) == 1
    res2 = client.get(
        "databrowser/freva/file",
        params={"time": "1898 to 1901", "time_select": "foo"},
    )
    assert res2.status_code == 500
    res3 = client.get("databrowser/freva/file", params={"time": "fx"})
    assert res3.status_code == 500


def test_facet_search(client: TestClient) -> None:
    """Test the facet search functionality."""
    res1 = client.get(
        "facet_search/cmip6/uri", params={"start": 0, "activity_id": "cmip"}
    ).json()
    assert len(res1["search_results"]) > 0
    assert "activity_id" in res1["facets"]
    res2 = client.get(
        "facet_search/cmip6/uri", params={"start": 1000, "activity_id": "cmip"}
    ).json()
    assert "rcm_name" not in res2["primary_facets"]
    assert res2["search_results"] == []
    res3 = client.get(
        "facet_search/cmip5/uri",
        params={"activity_id": "cmip", "translate": "false"},
    )
    assert res3.status_code == 400
    res4 = client.get(
        "facet_search/cmip5/uri",
        params={"activity_id": "cmip", "translate": "true"},
    )
    assert res4.status_code == 400
    res5 = client.get(
        "facet_search/cordex/uri",
        params={"domain": "eur-11", "translate": "true", "batch_size": "f"},
    ).json()
    assert "rcm_name" in res5["facets"]
    assert "rcm_name" in res5["primary_facets"]


def test_intake_search(client: TestClient) -> None:
    """Test the creation of intake catalogues."""
    res1 = client.get(
        "intake_catalogue/cmip6/uri",
        params={"activity_id": "cmip", "batch_size": 3},
    )
    assert res1.json() == json.loads(res1.text)
    res2 = client.get(
        "intake_catalogue/cmip6/uri",
        params={"batch_size": 3},
    )
    assert len(res2.json()["catalog_dict"]) > len(res1.json()["catalog_dict"])


def test_bad_intake_request(client: TestClient) -> None:
    """Test for a wrong intake request."""
    res1 = client.get(
        "intake_catalogue/cmip6/uri", params={"activity_ids": "cmip"}
    )
    res2 = client.get(
        "intake_catalogue/cmip6/uri", params={"activity_id": "cmip2"}
    )
    assert res2.status_code == res1.status_code == 400
