#!/usr/bin/env bash
set -e

CHECKPOINT_DIR="${CHECKPOINT_DIR:-/app/checkpoints}"
VOICE_FILE="${VOICE_FILE:-/app/voices/reference.wav}"
MODEL_VERSION="${MODEL_VERSION:-v2}"
URI="${URI:-tcp://0.0.0.0:10300}"
FP16="${FP16:-true}"
DEBUG="${DEBUG:-false}"

# Generation quality parameters
TOP_P="${TOP_P:-0.8}"
TOP_K="${TOP_K:-30}"
TEMPERATURE="${TEMPERATURE:-0.8}"
NUM_BEAMS="${NUM_BEAMS:-3}"
REPETITION_PENALTY="${REPETITION_PENALTY:-10.0}"
MAX_MEL_TOKENS="${MAX_MEL_TOKENS:-1500}"

# Download model checkpoints if not present
if [ ! -f "${CHECKPOINT_DIR}/config.yaml" ]; then
    echo "Downloading IndexTTS-2 model checkpoints..."
    pip install -q huggingface_hub[cli] 2>/dev/null || true
    huggingface-cli download IndexTeam/IndexTTS-2 --local-dir="${CHECKPOINT_DIR}"
fi

# Generate a default reference voice if none is provided
if [ ! -f "${VOICE_FILE}" ] || ! python3 -c "
import wave, sys
try:
    w = wave.open('${VOICE_FILE}', 'rb')
    w.close()
except:
    sys.exit(1)
" 2>/dev/null; then
    echo "No valid reference voice found at ${VOICE_FILE}"
    echo "Generating a silent placeholder..."
    echo "WARNING: For proper voice cloning, mount a real voice WAV file to ${VOICE_FILE}"
    python3 -c "
import wave, struct
with wave.open('${VOICE_FILE}', 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(22050)
    # 3 seconds of silence
    w.writeframes(b'\x00' * 22050 * 2 * 3)
"
    echo "Generated placeholder voice at ${VOICE_FILE}"
fi

ARGS=(
    --voice "${VOICE_FILE}"
    --checkpoint-dir "${CHECKPOINT_DIR}"
    --model-version "${MODEL_VERSION}"
    --uri "${URI}"
    --top-p "${TOP_P}"
    --top-k "${TOP_K}"
    --temperature "${TEMPERATURE}"
    --num-beams "${NUM_BEAMS}"
    --repetition-penalty "${REPETITION_PENALTY}"
    --max-mel-tokens "${MAX_MEL_TOKENS}"
)

if [ "${FP16}" = "true" ]; then
    ARGS+=(--fp16)
fi

if [ "${DEBUG}" = "true" ]; then
    ARGS+=(--debug)
fi

echo "Starting Wyoming IndexTTS server..."
echo "  Voice: ${VOICE_FILE}"
echo "  Checkpoints: ${CHECKPOINT_DIR}"
echo "  Model: ${MODEL_VERSION}"
echo "  URI: ${URI}"
echo "  FP16: ${FP16}"

exec python3 -m wyoming_indextts "${ARGS[@]}"
