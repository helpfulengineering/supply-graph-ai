import pytest
import asyncio
from uuid import uuid4

from core.services.storage_service import StorageService, OKHStorageHandler, OKWStorageHandler
from core.models.okh import OKHManifest, License, Person
from core.models.okw import ManufacturingFacility, Location, FacilityStatus, Address, What3Words


@pytest.mark.asyncio
async def test_okh_storage_handler_crud():
    storage_service = await StorageService.get_instance()
    handler = OKHStorageHandler(storage_service)

    # Create sample OKHManifest
    okh = OKHManifest(
        title="Test Manifest",
        repo="https://github.com/example/repo",
        version="1.0",
        license=License(hardware="MIT"),  # At least one license field must be set
        licensor=Person(name="Jane Doe", email="jane@example.com"),
        documentation_language="en",
        function="Demonstration of OKHManifest"
    )

    # Save
    etag = await handler.save(okh)
    assert etag

    # Load
    loaded = await handler.load(okh.id)
    assert loaded.id == okh.id
    assert loaded.title == okh.title

    # List
    objs = await handler.list()
    assert any(obj["id"] == okh.id for obj in objs)

    # Update
    okh.title = "Updated Title"
    await handler.save(okh)
    loaded2 = await handler.load(okh.id)
    assert loaded2.title == "Updated Title"

    # Delete
    deleted = await handler.delete(okh.id)
    assert deleted
    with pytest.raises(Exception):
        await handler.load(okh.id)

@pytest.mark.asyncio
async def test_okw_storage_handler_crud():
    storage_service = await StorageService.get_instance()
    handler = OKWStorageHandler(storage_service)
    facility_status = FacilityStatus.ACTIVE

    location = Location(city="Testville", country="Testland")

    address = Address(
        number="123",
        street="Main St",
        city="Testville",
        country="Testland"
    )
    what3words = What3Words(words="index.home.raft", language="en")
    location = Location(
        address=address,
        gps_coordinates="12.3456,78.9012",
        directions="Near the big tree",
        what3words=what3words,
        city="Testville",
        country="Testland"
    )

    okw = ManufacturingFacility(
        id=uuid4(),
        location=location,
        facility_status=facility_status,
        name="Test Facility"
    )

    # Save
    etag = await handler.save(okw)
    assert etag

    # Load
    loaded = await handler.load(okw.id)
    assert loaded.id == okw.id
    assert loaded.name == okw.name

    # List
    objs = await handler.list()
    assert any(obj["id"] == okw.id for obj in objs)

    # Update
    okw.name = "Updated Facility"
    await handler.save(okw)
    loaded2 = await handler.load(okw.id)
    assert loaded2.name == "Updated Facility"

    # Delete
    deleted = await handler.delete(okw.id)
    assert deleted
    with pytest.raises(Exception):
        await handler.load(okw.id) 