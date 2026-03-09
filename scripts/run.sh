#!/usr/bin/env bash
set -e

CHECKPOINT_DIR="${CHECKPOINT_DIR:-/app/checkpoints}"
VOICES_DIR="${VOICES_DIR:-/app/voices}"
DEFAULT_VOICE="${DEFAULT_VOICE:-}"
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

# Ensure voices directory exists
mkdir -p "${VOICES_DIR}"

# Check for at least one WAV file
WAV_COUNT=$(ls -1 "${VOICES_DIR}"/*.wav 2>/dev/null | wc -l)
if [ "${WAV_COUNT}" -eq 0 ]; then
    echo "No .wav files found in ${VOICES_DIR}"
    echo "Generating a placeholder voice..."
    echo "WARNING: For proper voice cloning, mount real voice WAV files to ${VOICES_DIR}/"
    python3 -c "
import wave
with wave.open('${VOICES_DIR}/default.wav', 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(22050)
    w.writeframes(b'\x00' * 22050 * 2 * 3)
"
    echo "Generated placeholder at ${VOICES_DIR}/default.wav"
fi

echo "Voices in ${VOICES_DIR}:"
ls -1 "${VOICES_DIR}"/*.wav 2>/dev/null || true

ARGS=(
    --voices-dir "${VOICES_DIR}"
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

if [ -n "${DEFAULT_VOICE}" ]; then
    ARGS+=(--default-voice "${DEFAULT_VOICE}")
fi

if [ "${FP16}" = "true" ]; then
    ARGS+=(--fp16)
fi

if [ "${DEBUG}" = "true" ]; then
    ARGS+=(--debug)
fi

echo "Starting Wyoming IndexTTS server..."
echo "  Voices dir: ${VOICES_DIR}"
echo "  Default voice: ${DEFAULT_VOICE:-<first found>}"
echo "  Checkpoints: ${CHECKPOINT_DIR}"
echo "  Model: ${MODEL_VERSION}"
echo "  URI: ${URI}"
echo "  FP16: ${FP16}"

exec python3 -m wyoming_indextts "${ARGS[@]}"
