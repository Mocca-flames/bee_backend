# WinSMS REST API Quick Reference Guide

## Base Configuration

**Base URL**: `https://api.winsms.co.za/api/rest/v1`

**Authentication**: Add your API key to the request header:

```
AUTHORIZATION: YOUR_API_KEY_HERE
```

**Content-Type**: `application/json`

## 1. Send SMS Messages

### Single SMS

**Endpoint**: `POST /sms/outbound`

**Request Headers**:

```
AUTHORIZATION: YOUR_API_KEY
Content-Type: application/json
```

**Request Body**:

```json
{
  "messages": [
    {
      "mobileNumber": "27821234567",
      "message": "Your SMS message content here"
    }
  ]
}
```

**Optional Parameters**:

```json
{
  "messages": [
    {
      "mobileNumber": "27821234567",
      "message": "Your SMS message content here",
      "clientMessageId": "your-unique-id-123",
      "scheduledTime": "2024-12-25 09:00:00"
    }
  ]
}
```

**Success Response** (200):

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 200,
  "messages": [
    {
      "apiMessageId": 12345678,
      "acceptedTime": "2024-01-01 12:00:00",
      "creditCost": 1.0,
      "newCreditBalance": 99.0,
      "mobileNumber": "27821234567",
      "clientMessageId": "your-unique-id-123"
    }
  ]
}
```

### Bulk SMS

**Endpoint**: `POST /sms/outbound`

**Request Body**:

```json
{
  "messages": [
    {
      "mobileNumber": "27821234567",
      "message": "Message 1"
    },
    {
      "mobileNumber": "27827654321",
      "message": "Message 2"
    },
    {
      "mobileNumber": "27829876543",
      "message": "Message 3"
    }
  ]
}
```

## 2. Check Credit Balance

**Endpoint**: `GET /credits/balance`

**Request Headers**:

```
AUTHORIZATION: YOUR_API_KEY
```

**Success Response** (200):

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 200,
  "creditBalance": 150.5
}
```

## 3. Get Message Status

**Endpoint**: `GET /sms/outbound/status/{apiMessageId}`

**Request Headers**:

```
AUTHORIZATION: YOUR_API_KEY
```

**URL Parameters**:

- `apiMessageId`: The message ID returned from sending SMS

**Success Response** (200):

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 200,
  "apiMessageId": 12345678,
  "mobileNumber": "27821234567",
  "statusCode": 10,
  "statusDescription": "Delivered",
  "creditCost": 1.0
}
```

**Status Codes**:

- `1`: Scheduled
- `2`: Sent
- `10`: Delivered
- `11`: Failed
- `22`: Unknown
- `23`: Expired

## 4. Get Multiple Message Statuses

**Endpoint**: `POST /sms/outbound/status`

**Request Body**:

```json
{
  "apiMessageIds": [12345678, 12345679, 12345680]
}
```

**Success Response** (200):

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 200,
  "messages": [
    {
      "apiMessageId": 12345678,
      "mobileNumber": "27821234567",
      "statusCode": 10,
      "statusDescription": "Delivered",
      "creditCost": 1.0
    }
  ]
}
```

## 5. Get Incoming SMS Messages

**Endpoint**: `GET /sms/inbound`

**Request Headers**:

```
AUTHORIZATION: YOUR_API_KEY
```

**Success Response** (200):

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 200,
  "incomingMessages": [
    {
      "mobileNumber": "27821234567",
      "message": "Incoming message text",
      "receiveTime": "2024-01-01 12:00:00",
      "apiMessageId": 12345678
    }
  ]
}
```

## Python Implementation Examples

### Basic Request Function

```python
import requests
import json

def make_winsms_request(method, endpoint, data=None):
    url = f"https://api.winsms.co.za/api/rest/v1{endpoint}"
    headers = {
        "AUTHORIZATION": "YOUR_API_KEY",
        "Content-Type": "application/json"
    }

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)

    return {
        "status_code": response.status_code,
        "data": response.json() if response.content else None
    }
```

### Send SMS

```python
def send_sms(mobile_number, message):
    data = {
        "messages": [{
            "mobileNumber": mobile_number,
            "message": message
        }]
    }
    return make_winsms_request("POST", "/sms/outbound", data)

# Usage
result = send_sms("27821234567", "Test message")
if result["status_code"] == 200:
    message_id = result["data"]["messages"][0]["apiMessageId"]
    print(f"SMS sent! Message ID: {message_id}")
```

### Check Credit Balance

```python
def get_credit_balance():
    return make_winsms_request("GET", "/credits/balance")

# Usage
balance = get_credit_balance()
if balance["status_code"] == 200:
    print(f"Credits remaining: {balance['data']['creditBalance']}")
```

### Check Message Status

```python
def get_message_status(api_message_id):
    return make_winsms_request("GET", f"/sms/outbound/status/{api_message_id}")

# Usage
status = get_message_status(12345678)
if status["status_code"] == 200:
    print(f"Status: {status['data']['statusDescription']}")
```

### Send Bulk SMS

```python
def send_bulk_sms(messages_list):
    data = {"messages": messages_list}
    return make_winsms_request("POST", "/sms/outbound", data)

# Usage
messages = [
    {"mobileNumber": "27821234567", "message": "Message 1"},
    {"mobileNumber": "27827654321", "message": "Message 2"}
]
result = send_bulk_sms(messages)
```

## Error Responses

**401 Unauthorized**:

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 401,
  "errorMessage": "The 'AUTHORIZATION' header was not found. Set the 'AUTHORIZATION' request header to your WinSMS API Key"
}
```

**404 Not Found**:

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 404,
  "errorMessage": "The resource requested does not exist. Please verify the path, spelling, and capitalisation"
}
```

**405 Method Not Allowed**:

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 405,
  "errorMessage": "Request method should be set to 'POST', not 'GET'."
}
```

**500 Internal Server Error**:

```json
{
  "timeStamp": "20240101120000000",
  "version": "1.0",
  "statusCode": 500,
  "errorMessage": "An unknown error has occurred - authorising API Key"
}
```

## Quick Integration Tips

### Phone Number Format

- Must be in international format: `27XXXXXXXXX` (South Africa)
- Remove spaces, dashes, or brackets
- Don't include the `+` symbol

### Message Length

- Single SMS: 160 characters max
- Unicode/emoji messages: 70 characters max
- Longer messages will be split and charged accordingly

### Rate Limits

- No official rate limit specified
- Recommend max 10 requests per second for bulk operations

### Required Fields

- `mobileNumber`: Always required
- `message`: Always required
- `AUTHORIZATION` header: Always required

### Optional Fields

- `clientMessageId`: Your unique reference (useful for tracking)
- `scheduledTime`: Format `YYYY-MM-DD HH:MM:SS` (future dates only)

This guide gives you everything you need to integrate WinSMS REST API into your existing Python project quickly!
