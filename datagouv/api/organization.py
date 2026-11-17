import logging
from collections.abc import Iterator
from typing import ClassVar

from datagouv.api.client import DEFAULT_CLIENT, Client
from datagouv.api.dataset import Dataset, DatasetCreator
from datagouv.utils.base_object import BaseObject, Creator, assert_auth
from datagouv.utils.errors import DatagouvAPIError
from datagouv.utils.retry import simple_connection_retry

logger = logging.getLogger(__name__)


class Organization(BaseObject):
    _datasets: list[Dataset] | None = None
    _attributes: ClassVar[list[str]] = [
        "badges",
        "business_number_id",
        "created_at",
        "deleted",
        "description",
        "last_modified",
        "members",
        "metrics",
        "name",
        "url",
        "extras",
    ]

    def __init__(
        self,
        id: str,
        fetch: bool = True,
        _client: Client = DEFAULT_CLIENT,
        _from_response: dict | None = None,
    ):
        BaseObject.__init__(self, id, _client)
        self.uri = f"{_client.base_url}/api/1/organizations/{id}/"
        self.front_url = self.uri.replace("/api/1", "")
        if fetch or _from_response:
            self.refresh(_from_response=_from_response)

    def __call__(self, *args, **kwargs):
        return Organization(*args, **kwargs)

    def refresh(self, _from_response: dict | None = None):
        metadata = super().refresh(_from_response)
        self._datasets = None
        return metadata

    @property
    def datasets(self) -> Iterator[Dataset]:
        if self._datasets is None:
            self._datasets = [
                Dataset(item["id"], _client=self._client, _from_response=item)
                for item in self._client.get_all_from_api_query(
                    f"api/1/organizations/{self.id}/datasets/"
                )
            ]
        yield from self._datasets

    def create_dataset(self, payload: dict) -> Dataset:
        # we don't simply heritate from DatasetCreator to have a different method name
        for key in ["organization", "owner"]:
            if payload.get(key):
                raise ValueError(
                    f"It is not possible to specify the {key} when creating a dataset "
                    "from an organization, it will be attached to it."
                )
        return DatasetCreator(_client=self._client).create(
            payload=payload | {"organization": self.id}
        )


class OrganizationCreator(Creator):
    @simple_connection_retry
    def create(self, payload: dict) -> Organization:
        assert_auth(self._client)
        if self._client.verbose:
            logger.info(f"Creating organization '{payload['name']}'")
        r = self._client.session.post(f"{self._client.base_url}/api/1/organizations/", json=payload)
        try:
            r.raise_for_status()
        except Exception as e:
            raise DatagouvAPIError(r.text) from e
        metadata = r.json()
        return Organization(metadata["id"], _client=self._client, _from_response=metadata)
