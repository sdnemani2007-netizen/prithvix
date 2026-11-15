from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_farm_crud_cycle():
    # 1. Create a test farm
    payload = {
        "name": "Medchal Test Farm",
        "farmer_name": "Ramesh Patel",
        "location": "Medchal, Telangana, India",
        "latitude": 17.629,
        "longitude": 78.481,
        "area": 4.5,
        "area_unit": "Acres",
        "current_crop": "Rice / Paddy",
        "soil_type": "Black Cotton Soil (Vertisol)",
        "water_source": "Borehole / Groundwater",
        "irrigation_method": "Drip Irrigation",
        "primary_goal": "Increase Crop Yield & Quality",
        "timezone": "Asia/Kolkata",
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [78.480, 17.628],
                [78.482, 17.628],
                [78.482, 17.630],
                [78.480, 17.630],
                [78.480, 17.628]
            ]]
        }
    }

    create_res = client.post("/api/farms", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    farm_id = created_data["id"]
    assert farm_id is not None
    assert created_data["name"] == "Medchal Test Farm"
    assert created_data["climate_zone"] == "trop"

    # 2. Retrieve farm
    get_res = client.get(f"/api/farms/{farm_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Medchal Test Farm"

    # 3. List farms
    list_res = client.get("/api/farms")
    assert list_res.status_code == 200
    farms_list = list_res.json()
    assert any(f["id"] == farm_id for f in farms_list)

    # 4. Update farm
    update_res = client.put(f"/api/farms/{farm_id}", json={"current_crop": "Cotton", "area": 5.0})
    assert update_res.status_code == 200
    assert update_res.json()["current_crop"] == "Cotton"
    assert update_res.json()["area"] == 5.0

    # 5. Delete farm
    del_res = client.delete(f"/api/farms/{farm_id}")
    assert del_res.status_code == 204

    # 6. Verify deleted
    get_deleted = client.get(f"/api/farms/{farm_id}")
    assert get_deleted.status_code == 404


def test_invalid_coordinates():
    payload = {
        "name": "Invalid Coordinates Farm",
        "location": "Nowhere",
        "latitude": 195.0,  # Invalid latitude (>90)
        "longitude": 78.0
    }
    res = client.post("/api/farms", json=payload)
    assert res.status_code == 422  # Pydantic validation error
