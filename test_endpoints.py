import requests
import json

# Base URL for the local server
BASE_URL = "http://localhost:8000"

# Endpoints for students
STUDENTS_ENDPOINT = f"{BASE_URL}/students"
STUDENT_STATISTICS_ENDPOINT = f"{BASE_URL}/students/statistics"
STUDENT_GRADES_ENDPOINT = f"{BASE_URL}/students/grades"

# Endpoints for SMS
SMS_FEE_NOTIFICATION_ENDPOINT = f"{BASE_URL}/sms/fee-notification"
SMS_BULK_ENDPOINT = f"{BASE_URL}/sms/bulk"
SMS_HISTORY_ENDPOINT = f"{BASE_URL}/sms/history"

def test_students_endpoint():
    response = requests.get(STUDENTS_ENDPOINT)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    print("Students endpoint test passed")

def test_create_student_endpoint():
    student_data = {
        "name": "Test Student",
        "grade": "Grade 1",
        "parent1_phone": "+1234567890",
        "fee_status": "unpaid"
    }
    response = requests.post(STUDENTS_ENDPOINT, json=student_data)
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"
    print("Create student endpoint test passed")

def test_student_statistics_endpoint():
    response = requests.get(STUDENT_STATISTICS_ENDPOINT)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    print("Student statistics endpoint test passed")

def test_student_grades_endpoint():
    response = requests.get(STUDENT_GRADES_ENDPOINT)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    print("Student grades endpoint test passed")

def test_sms_fee_notification_endpoint():
    fee_notification_data = {
        "student_ids": ["valid_student_id"],
        "template_name": "fee_notification_template"
    }
    response = requests.post(SMS_FEE_NOTIFICATION_ENDPOINT, json=fee_notification_data)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    print("SMS fee notification endpoint test passed")

def test_sms_bulk_endpoint():
    bulk_sms_data = {
        "message": "Test bulk SMS message",
        "filters": {
            "grades": ["Grade 1"],
            "fee_status": "unpaid"
        }
    }
    response = requests.post(SMS_BULK_ENDPOINT, json=bulk_sms_data)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    print("SMS bulk endpoint test passed")

def test_sms_history_endpoint():
    response = requests.get(SMS_HISTORY_ENDPOINT)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    print("SMS history endpoint test passed")

def main():
    test_students_endpoint()
    test_create_student_endpoint()
    test_student_statistics_endpoint()
    test_student_grades_endpoint()
    test_sms_fee_notification_endpoint()
    test_sms_bulk_endpoint()
    test_sms_history_endpoint()

if __name__ == "__main__":
    main()
