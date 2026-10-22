from unittest.mock import patch

import pytest
from conftest import (
    DATAGOUV_URL,
    DATASERVICE_ID,
    ORGANIZATION_ID,
    dataservice_metadata,
    dataset_metadata,
    organization_metadata,
)

from datagouv.api.client import Client
from datagouv.api.dataset import Dataset
from datagouv.api.dataservice import Dataservice
from datagouv.api.organization import Organization
from datagouv.utils.base_object import BaseObject


def test_dataservice_instance(dataservice_api_call):
    assert isinstance(Client().dataservice(DATASERVICE_ID), Dataservice)


def test_dataservice_attributes_and_methods(dataservice_api_call):
    client = Client()
    ds = client.dataservice(DATASERVICE_ID)
    with patch("niquests.Session.get") as mock_func:
        ds_from_response = Dataservice(
            dataservice_metadata["id"], _from_response=dataservice_metadata
        )
        mock_func.assert_not_called()
    for attribute in (
        ["id", "uri", "front_url", "organization_id", "associated_datasets"]
        + Dataservice._attributes
        + [method for method in dir(BaseObject) if not method.startswith("__")]
    ):
        assert attribute in dir(ds)
        assert attribute in dir(ds_from_response)


def test_dataservice_no_fetch():
    with patch("niquests.Session.get") as mock_func:
        ds = Dataservice(DATASERVICE_ID, fetch=False)
        mock_func.assert_not_called()
    assert all(getattr(ds, attr, None) is None for attr in Dataservice._attributes)
    assert ds.uri


def test_authentication_assertion():
    client = Client()
    with pytest.raises(PermissionError):
        client.create_dataservice({"title": "Test API"})
    ds = Dataservice(DATASERVICE_ID, _from_response=dataservice_metadata)
    with pytest.raises(PermissionError):
        ds.delete()
    with pytest.raises(PermissionError):
        ds.update({})
    with pytest.raises(PermissionError):
        ds.update_extras({})
    with pytest.raises(PermissionError):
        ds.delete_extras([])


def test_dataservice_update(dataservice_api_call, niquests_mock):
    updated_metadata = dataservice_metadata.copy()
    payload = {"title": "Updated API Title", "description": "Updated description"}
    niquests_mock.patch(f"{DATAGOUV_URL}api/1/dataservices/{DATASERVICE_ID}/").respond(
        json=updated_metadata | payload,
        status_code=200,
    )
    client = Client(api_key="test-api-key")
    ds = client.dataservice(DATASERVICE_ID)
    response = ds.update(payload)
    assert response.status_code == 200
    for attr in payload:
        assert getattr(ds, attr) == payload[attr]


def test_dataservice_update_invalid_payload():
    client = Client(api_key="test-api-key")
    ds = Dataservice(DATASERVICE_ID, _client=client, _from_response=dataservice_metadata)
    with pytest.raises(TypeError):
        ds.update("not a dict")


def test_dataservice_create(niquests_mock):
    niquests_mock.post(f"{DATAGOUV_URL}api/1/dataservices/").respond(
        json=dataservice_metadata,
        status_code=201,
    )
    client = Client(api_key="test-api-key")
    created = client.create_dataservice(
        {"title": "New API", "organization": ORGANIZATION_ID}
    )
    assert isinstance(created, Dataservice)
    for attr in Dataservice._attributes:
        assert getattr(created, attr) == dataservice_metadata[attr]


def test_dataservice_delete(dataservice_api_call, niquests_mock):
    niquests_mock.delete(f"{DATAGOUV_URL}api/1/dataservices/{DATASERVICE_ID}/").respond(
        status_code=204
    )
    client = Client(api_key="test-api-key")
    ds = client.dataservice(DATASERVICE_ID)
    response = ds.delete()
    assert response.status_code == 204


def test_organization_id():
    ds = Dataservice(DATASERVICE_ID, _from_response=dataservice_metadata)
    assert ds.organization_id == ORGANIZATION_ID


def test_associated_datasets(niquests_mock):
    niquests_mock.get(f"{DATAGOUV_URL}api/1/datasets/?dataservice={DATASERVICE_ID}").respond(
        json={"data": [dataset_metadata], "next_page": None}
    )
    ds = Dataservice(DATASERVICE_ID, _from_response=dataservice_metadata)
    datasets = list(ds.associated_datasets)
    assert len(datasets) == 1
    assert isinstance(datasets[0], Dataset)


def test_associated_datasets_slug():
    slug = "my-api-slug"
    ds = Dataservice(slug, _from_response=dataservice_metadata)
    with pytest.raises(Exception, match="slug"):
        list(ds.associated_datasets)


def test_organization_create_dataservice(niquests_mock):
    niquests_mock.post(f"{DATAGOUV_URL}api/1/dataservices/").respond(
        json=dataservice_metadata,
        status_code=201,
    )
    client = Client(api_key="test-api-key")
    org = Organization(ORGANIZATION_ID, _client=client, _from_response=organization_metadata)
    created = org.create_dataservice({"title": "New API"})
    assert isinstance(created, Dataservice)


def test_client_dataservice_methods():
    client = Client()
    assert hasattr(client, "dataservice")
    assert hasattr(client, "create_dataservice")
