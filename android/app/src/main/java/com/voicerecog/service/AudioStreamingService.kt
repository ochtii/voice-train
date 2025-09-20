package com.voicerecog.android.service

import android.app.*
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Binder
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.voicerecog.android.R
import com.voicerecog.android.repository.AudioRepository
import com.voicerecog.android.repository.DeviceRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.*
import timber.log.Timber
import java.nio.ByteBuffer
import javax.inject.Inject

/**
 * Foreground service for continuous audio streaming to Raspberry Pi
 */
@AndroidEntryPoint
class AudioStreamingService : Service() {

    companion object {
        const val ACTION_START_STREAMING = "START_STREAMING"
        const val ACTION_STOP_STREAMING = "STOP_STREAMING"
        const val NOTIFICATION_ID = 1001
        const val CHANNEL_ID = "AUDIO_STREAMING_CHANNEL"
        
        // Audio configuration
        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val BUFFER_SIZE_FACTOR = 2
    }

    @Inject
    lateinit var audioRepository: AudioRepository
    
    @Inject
    lateinit var deviceRepository: DeviceRepository

    private val binder = AudioStreamingBinder()
    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordingJob: Job? = null
    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())

    inner class AudioStreamingBinder : Binder() {
        fun getService(): AudioStreamingService = this@AudioStreamingService
    }

    override fun onCreate() {
        super.onCreate()
        Timber.i("AudioStreamingService created")
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START_STREAMING -> {
                startAudioStreaming()
            }
            ACTION_STOP_STREAMING -> {
                stopAudioStreaming()
                stopSelf()
            }
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder = binder

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Audio Streaming",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Voice recognition audio streaming"
            setShowBadge(false)
            setSound(null, null)
        }

        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.createNotificationChannel(channel)
    }

    private fun createNotification(): Notification {
        val stopIntent = Intent(this, AudioStreamingService::class.java).apply {
            action = ACTION_STOP_STREAMING
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 0, stopIntent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Voice Recognition")
            .setContentText("Streaming audio to Raspberry Pi")
            .setSmallIcon(R.drawable.ic_mic)
            .setOngoing(true)
            .setShowWhen(false)
            .addAction(
                R.drawable.ic_stop,
                "Stop",
                stopPendingIntent
            )
            .build()
    }

    private fun startAudioStreaming() {
        if (isRecording) {
            Timber.w("Already recording")
            return
        }

        try {
            val bufferSize = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT
            ) * BUFFER_SIZE_FACTOR

            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Timber.e("Failed to initialize AudioRecord")
                return
            }

            startForeground(NOTIFICATION_ID, createNotification())

            audioRecord?.startRecording()
            isRecording = true

            recordingJob = serviceScope.launch {
                streamAudioData()
            }

            Timber.i("Audio streaming started")

        } catch (e: SecurityException) {
            Timber.e(e, "Missing audio permission")
        } catch (e: Exception) {
            Timber.e(e, "Error starting audio streaming")
        }
    }

    private suspend fun streamAudioData() {
        val audioRecord = this.audioRecord ?: return
        val bufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT
        )
        
        val buffer = ByteArray(bufferSize)
        var consecutiveErrors = 0

        while (isRecording && !currentCoroutineContext().job.isCancelled) {
            try {
                val bytesRead = audioRecord.read(buffer, 0, buffer.size)
                
                if (bytesRead > 0) {
                    consecutiveErrors = 0
                    
                    // Calculate audio level for UI feedback
                    val audioLevel = calculateAudioLevel(buffer, bytesRead)
                    audioRepository.updateAudioLevel(audioLevel)
                    
                    // Send audio data to Raspberry Pi
                    deviceRepository.sendAudioData(buffer.copyOf(bytesRead))
                    
                } else {
                    consecutiveErrors++
                    Timber.w("AudioRecord read error: $bytesRead")
                    
                    if (consecutiveErrors > 10) {
                        Timber.e("Too many consecutive audio read errors, stopping")
                        break
                    }
                    
                    delay(10) // Brief delay before retry
                }
                
            } catch (e: Exception) {
                Timber.e(e, "Error in audio streaming loop")
                consecutiveErrors++
                
                if (consecutiveErrors > 5) {
                    break
                }
                
                delay(100) // Longer delay on exception
            }
        }
        
        Timber.i("Audio streaming loop ended")
    }

    private fun calculateAudioLevel(buffer: ByteArray, bytesRead: Int): Float {
        try {
            val samples = bytesRead / 2 // 16-bit samples
            var sum = 0L
            
            for (i in 0 until samples) {
                val sample = ((buffer[i * 2 + 1].toInt() shl 8) or 
                             (buffer[i * 2].toInt() and 0xFF)).toShort()
                sum += (sample * sample).toLong()
            }
            
            val rms = kotlin.math.sqrt(sum.toDouble() / samples)
            val maxValue = Short.MAX_VALUE.toDouble()
            
            // Normalize to 0-1 range
            return (rms / maxValue).toFloat().coerceIn(0f, 1f)
            
        } catch (e: Exception) {
            Timber.e(e, "Error calculating audio level")
            return 0f
        }
    }

    private fun stopAudioStreaming() {
        Timber.i("Stopping audio streaming")
        
        isRecording = false
        recordingJob?.cancel()
        
        audioRecord?.apply {
            if (state == AudioRecord.STATE_INITIALIZED) {
                stop()
            }
            release()
        }
        audioRecord = null
        
        audioRepository.updateAudioLevel(0f)
        stopForeground(STOP_FOREGROUND_REMOVE)
        
        Timber.i("Audio streaming stopped")
    }

    override fun onDestroy() {
        super.onDestroy()
        stopAudioStreaming()
        serviceScope.cancel()
        Timber.i("AudioStreamingService destroyed")
    }
}