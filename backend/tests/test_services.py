from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_farm_services_integration():
    # Create a test farm
    payload = {
        "name": "Integration Agri Farm",
        "farmer_name": "Kavitha Reddy",
        "location": "Warangal, Telangana",
        "latitude": 17.978,
        "longitude": 79.594,
        "area": 3.0,
        "area_unit": "Acres",
        "current_crop": "Cotton",
        "soil_type": "Black Cotton Soil (Vertisol)",
        "water_source": "Borehole / Groundwater",
        "irrigation_method": "Drip Irrigation",
        "primary_goal": "Reduce Water Consumption",
        "timezone": "Asia/Kolkata"
    }
    farm_res = client.post("/api/farms", json=payload)
    assert farm_res.status_code == 201
    farm_id = farm_res.json()["id"]

    try:
        # 1. Test Dashboard endpoint
        dash_res = client.get(f"/api/dashboard/{farm_id}")
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert dash_data["farm_id"] == farm_id
        assert dash_data["farm_name"] == "Integration Agri Farm"
        assert len(dash_data["plots"]) >= 2
        assert len(dash_data["recommended_actions"]) > 0

        # 2. Test Crop Recommendations
        crops_res = client.get(f"/api/crops/recommendations/{farm_id}")
        assert crops_res.status_code == 200
        crops_data = crops_res.json()
        assert len(crops_data["recommendations"]) > 0
        first_crop = crops_data["recommendations"][0]
        assert "n" in first_crop
        assert "sc" in first_crop
        assert "why" in first_crop

        # 3. Test Crop Rotation
        rot_res = client.get(f"/api/crops/rotation/{farm_id}")
        assert rot_res.status_code == 200
        rot_data = rot_res.json()
        assert "plans" in rot_data
        assert "Balanced Agro-Ecological" in rot_data["plans"]

        # 4. Test Irrigation Advisory
        irrig_res = client.get(f"/api/irrigation/{farm_id}")
        assert irrig_res.status_code == 200
        irrig_data = irrig_res.json()
        assert "advisory" in irrig_data
        assert "explanation" in irrig_data

        # 5. Test Alerts
        alerts_res = client.get(f"/api/alerts/{farm_id}")
        assert alerts_res.status_code == 200
        alerts_list = alerts_res.json()
        assert isinstance(alerts_list, list)

        # 6. Test PrithviXAI Chat endpoint
        chat_res = client.post("/api/chat", json={
            "message": "Is my soil moisture low and should I irrigate?",
            "farm_id": farm_id
        })
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "reply" in chat_data
        assert len(chat_data["reply"]) > 20
        assert "grounded_on" in chat_data
        assert chat_data["grounded_on"]["farm_name"] == "Integration Agri Farm"

    finally:
        # Cleanup
        client.delete(f"/api/farms/{farm_id}")
