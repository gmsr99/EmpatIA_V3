class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.bufferSize = 4096;
        this._buffer = new Float32Array(this.bufferSize);
        this._bytesWritten = 0;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        const inputChannel = input?.[0];

        if (!inputChannel || inputChannel.length === 0) return true;

        // Append to buffer
        // (Note: inputChannel usually 128 samples)
        if (this._bytesWritten + inputChannel.length > this.bufferSize) {
            this.flush();
        }

        this._buffer.set(inputChannel, this._bytesWritten);
        this._bytesWritten += inputChannel.length;

        if (this._bytesWritten >= this.bufferSize) {
            this.flush();
        }

        return true;
    }

    flush() {
        if (this._bytesWritten === 0) return;

        // Send only the filled part
        const dataToSend = this._buffer.slice(0, this._bytesWritten);

        // Calculate RMS for visualization
        let sum = 0;
        for (let i = 0; i < dataToSend.length; i++) {
            sum += dataToSend[i] * dataToSend[i];
        }
        const rms = Math.sqrt(sum / dataToSend.length);

        // Convert to PCM Int16
        const pcmData = new Int16Array(dataToSend.length);
        for (let i = 0; i < dataToSend.length; i++) {
            const s = Math.max(-1, Math.min(1, dataToSend[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        this.port.postMessage({
            type: 'audio',
            buffer: pcmData.buffer,
            rms: rms
        }, [pcmData.buffer]);

        this._bytesWritten = 0;
    }
}

registerProcessor('audio-processor', AudioProcessor);
