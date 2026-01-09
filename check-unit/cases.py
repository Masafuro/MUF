# muf/check_unit/cases.py
import asyncio
import traceback

async def test_state_management(client):
    print("\n[Step 1] Testing State Management (Send/Get)...")
    test_data = b"system_ok_2026"
    await client.send(status="keep", message_id="health_check", data=test_data)
    retrieved = await client.get_state(target_unit="check-unit", message_id="health_check")
    if retrieved == test_data:
        print(f"  Result: SUCCESS (Retrieved: {retrieved.decode()})")
    else:
        print(f"  Result: FAILED (Expected {test_data}, got {retrieved})")

async def test_echo_messaging(client):
    print("\n[Step 2] Testing Request/Response with 'echo-service'...")
    request_content = b"muf_integration_test"
    try:
        response = await client.request(
            target_unit="echo-service",
            data=request_content,
            timeout=5.0
        )
        print(f"  Result: SUCCESS (Echo Received: {response.decode()})")
    except asyncio.TimeoutError:
        print("  Result: FAILED (Request timed out)")

async def test_state_watching(client):
    print("\n[Step 3] Testing State Watching...")
    watch_received = asyncio.Event()
    async def watch_handler(unit, msg_id, data):
        print(f"  Notification Received: {unit}/{msg_id} = {data.decode()}")
        watch_received.set()

    await client.watch_state(target_unit="check-unit", message_id="notify_test", handler=watch_handler)
    await client.send(status="keep", message_id="notify_test", data=b"event_triggered")
    await asyncio.wait_for(watch_received.wait(), timeout=3.0)
    print("  Result: SUCCESS (Event handler executed)")