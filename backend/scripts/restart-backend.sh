#!/bin/bash
# Reliably restart the backend — kills only the exact PID, not itself.

PID_FILE=/tmp/legal-bot-be.pid

# Stop old process
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping old process $OLD_PID ..."
        kill "$OLD_PID"
        sleep 2
    fi
fi

# Also find any lingering uvicorn on port 8888
EXISTING=$(lsof -ti :8888 2>/dev/null)
if [ -n "$EXISTING" ]; then
    echo "Killing lingering process(es) on port 8888: $EXISTING"
    kill -9 $EXISTING 2>/dev/null
    sleep 1
fi

# Start new
cd /home/chaoyu/backend
nohup uvicorn app.main:app --reload --port 8888 --host 0.0.0.0 > /tmp/be.log 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
echo "Backend started, PID: $NEW_PID"
sleep 3
curl -s http://localhost:8888/health
