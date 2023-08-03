"""Unit tests for the freva databrowser module."""
import json

from fastapi.testclient import TestClient


def test_attributes(client: TestClient) -> None:
    """Test getting the attributes."""
    res1 = client.get("overview")
    assert isinstance(res1.json()["flavours"], list)
    assert isinstance(res1.json()["attributes"], dict)


def test_databrowser(client: TestClient) -> None:
    """Test the default databrowser functionality."""
    res1 = client.get(
        "databrowser/cmip6/uri",
        params={"batch_size": 2, "activity_id": "cmipx"},
    )
    assert res1.status_code == 400
    res2 = client.get(
        "databrowser/cmip6/uri",
        params={"translate": "false", "product": "cmip", "batch_size": 2},
    )
    res3 = client.get(
        "databrowser/freva/uri", params={"product": "cmip", "batch_size": 2}
    )
    assert len(res1.text.split()) == 0
    assert res2.text == res3.text
    res3 = client.get(
        "databrowser/freva/uri", params={"foo": "cmip", "batch_size": "t"}
    )
    assert res3.status_code == 422
    res4 = client.get("databrowser/cmip6/uri", params={"foo": "bar"})
    assert res4.status_code == 400


def test_time_selection(client: TestClient) -> None:
    """Test the time select functionality of the API."""
    res1 = client.get(
        "databrowser/freva/file",
        params={"time": "1898 to 1901", "batch_size": 2},
    )
    assert len(res1.text.split()) == 1
    res2 = client.get(
        "databrowser/freva/file",
        params={"time": "1898 to 1901", "time_select": "foo", "batch_size": 2},
    )
    assert res2.status_code == 500
    res3 = client.get(
        "databrowser/freva/file", params={"time": "fx", "batch_size": 2}
    )
    assert res3.status_code == 500


def test_primary_facets(client: TestClient) -> None:
    """Test the functionality of primary facet definitions."""
    res1 = client.get("metadata_search/freva/file").json()
    res2 = client.get("metadata_search/cmip6/file").json()
    res3 = client.get(
        "metadata_search/cmip6/file", params={"translate": "f"}
    ).json()
    assert "primary_facets" in res1
    assert "primary_facets" in res2
    assert "primary_facets" in res3
    assert (
        len(res1["primary_facets"])
        == len(res2["primary_facets"])
        == len(res3["primary_facets"])
    )
    assert res1["primary_facets"] == res3["primary_facets"]
    assert res1["primary_facets"] != res2["primary_facets"]


def test_metadata_search(client: TestClient) -> None:
    """Test the facet search functionality."""
    res1 = client.get(
        "metadata_search/cmip6/uri",
        params={"start": 0, "activity_id": "cmip", "batch_size": 2},
    ).json()
    assert len(res1["search_results"]) > 0
    assert "activity_id" in res1["facets"]
    res2 = client.get(
        "metadata_search/cmip6/uri",
        params={"start": 1000, "activity_id": "cmip", "batch_size": 2},
    ).json()
    assert "rcm_name" not in res2["primary_facets"]
    assert res2["search_results"] == []
    res3 = client.get(
        "metadata_search/cmip5/uri",
        params={"activity_id": "cmip", "translate": "false", "batch_size": 2},
    )
    assert res3.status_code == 400
    res4 = client.get(
        "metadata_search/cmip5/uri",
        params={"activity_id": "cmip", "translate": "true", "batch_size": 2},
    )
    assert res4.status_code == 400
    res5 = client.get(
        "metadata_search/cordex/uri",
        params={"domain": "eur-11", "translate": "true"},
    ).json()
    assert "rcm_name" in res5["facets"]
    assert "rcm_name" in res5["primary_facets"]

    res6 = client.get(
        "metadata_search/cmip6/uri", params={"facets": "activity_id"}
    ).json()
    assert len(res6["facets"].keys()) == 1


def test_intake_search(client: TestClient) -> None:
    """Test the creation of intake catalogues."""
    res1 = client.get(
        "intake_catalogue/cmip6/uri",
        params={"activity_id": "cmip", "batch_size": 2, "multi-version": True},
    )
    assert res1.json() == json.loads(res1.text)
    res2 = client.get(
        "intake_catalogue/cmip6/uri",
    )
    assert len(res2.json()["catalog_dict"]) > len(res1.json()["catalog_dict"])


def test_bad_intake_request(client: TestClient) -> None:
    """Test for a wrong intake request."""
    res1 = client.get(
        "intake_catalogue/cmip6/uri",
        params={"activity_ids": "cmip", "batch_size": 2},
    )
    res2 = client.get(
        "intake_catalogue/cmip6/uri",
        params={"activity_id": "cmip2", "batch_size": 2},
    )
    assert res2.status_code == res1.status_code == 400