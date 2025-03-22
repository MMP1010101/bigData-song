import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
from scipy.signal import find_peaks

def analyze_song(file_path):
    """
    Analyze a song and extract its timing features.
    """
    print(f"Loading and analyzing: {file_path}")
    
    # Load the audio file
    y, sr = librosa.load(file_path, sr=None)
    
    # Extract tempo (BPM)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    
    # Extract beat positions
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    # Extract onsets (note beginnings)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    
    # Segment the audio using harmonic changes
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    bounds = librosa.segment.agglomerative(chroma, 10)
    segment_times = librosa.frames_to_time(bounds, sr=sr)
    
    # Extract loudness over time
    rms = librosa.feature.rms(y=y)[0]
    rms_times = librosa.times_like(rms, sr=sr)
    
    # Calculate duration
    duration = librosa.get_duration(y=y, sr=sr)
    
    return {
        "tempo": tempo,
        "beat_times": beat_times,
        "onset_times": onset_times,
        "segment_times": segment_times,
        "rms": rms,
        "rms_times": rms_times,
        "duration": duration,
        "sr": sr,
        "y": y
    }

def generate_timing_prompt(features):
    """
    Generate a descriptive prompt about the song's timing structure.
    Includes detailed RMS energy analysis per second.
    """
    # Basic information
    prompt = f"This song has a tempo of approximately {features['tempo'].item():.1f} BPM (beats per minute).\n"
    prompt += f"It has a duration of {features['duration'] // 60:.0f} minutes and {features['duration'] % 60:.0f} seconds.\n\n"
    
    # Beat structure
    prompt += f"The song contains {len(features['beat_times'])} beats.\n"
    
    # Sections/segments
    prompt += f"The song can be divided into {len(features['segment_times'])} distinct sections based on harmonic changes.\n"
    
    # Timing markers for key sections
    prompt += "Key timing markers (in seconds):\n"
    
    for i, time in enumerate(features['segment_times']):
        if i == 0:
            prompt += f"- Start: 0.0\n"
        else:
            prompt += f"- Section change at: {time:.2f}\n"
    
    # Dynamic changes (loudness)
    rms = features['rms']
    rms_times = features['rms_times']
    
    # Find peaks in loudness (potential chorus or drops)
    peaks, _ = find_peaks(rms, height=np.mean(rms) * 1.2, distance=features['sr']//10)
    
    if len(peaks) > 0:
        prompt += "\nSignificant dynamic changes (potential chorus/drop sections):\n"
        for peak in peaks:
            if peak < len(rms_times):
                time = rms_times[peak]
                prompt += f"- Energy peak at: {time:.2f} seconds\n"
    
    # Add detailed RMS energy analysis per second
    prompt += "\nDetailed RMS Energy Analysis (second by second):\n"
    
    # Get RMS values and their timestamps
    rms_values = features['rms']
    rms_timestamps = features['rms_times']
    
    # Calculate the number of seconds in the audio
    duration_seconds = int(features['duration']) + 1
    
    # For each second, find the closest RMS value
    for second in range(duration_seconds):
        # Find the index of the closest timestamp to the current second
        closest_idx = np.argmin(np.abs(rms_timestamps - second))
        
        # Get the RMS value at this index
        rms_value = rms_values[closest_idx]
        
        # Add to the prompt
        prompt += f"- Second {second}: RMS Energy = {rms_value:.6f}\n"
    
    return prompt

def visualize_song(features, file_path=None):
    """
    Create visualizations of the song's features.
    If file_path is provided, saves the visualization as a PNG file.
    """
    y = features['y']
    sr = features['sr']
    
    plt.figure(figsize=(14, 10))
    
    # Plot waveform
    plt.subplot(3, 1, 1)
    librosa.display.waveshow(y, sr=sr)
    plt.title('Waveform')
    
    # Plot beats and segments
    plt.subplot(3, 1, 2)
    times = librosa.times_like(y, sr=sr)
    plt.plot(times, y)
    plt.vlines(features['beat_times'], -1, 1, color='r', alpha=0.5, label='Beats')
    plt.vlines(features['segment_times'], -1, 1, color='g', linewidth=2, label='Segments')
    plt.title('Beats and Segments')
    plt.legend()
    
    # Plot RMS energy
    plt.subplot(3, 1, 3)
    plt.plot(features['rms_times'], features['rms'])
    plt.title('RMS Energy (Loudness)')
    plt.xlabel('Time (s)')
    
    plt.tight_layout()
    
    # Save visualization if file_path is provided
    if file_path:
        output_file = Path(file_path).with_suffix('.png')
        plt.savefig(output_file)
        print(f"Visualization saved to: {output_file}")
    
    plt.show()

def save_prompt_to_file(prompt, file_path):
    """
    Save the analysis prompt to a text file.
    """
    output_file = Path(file_path).with_suffix('.txt')
    with open(output_file, 'w') as f:
        f.write(prompt)
    print(f"\nAnalysis saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze a song and generate timing descriptions.')
    parser.add_argument('file_path', type=str, help='Path to the audio file')
    parser.add_argument('--visualize', action='store_true', help='Generate visualizations')
    parser.add_argument('--save', action='store_true', help='Save the analysis to a text file')
    
    args = parser.parse_args()
    
    try:
        features = analyze_song(args.file_path)
        prompt = generate_timing_prompt(features)
        
        print("\n=== SONG TIMING ANALYSIS ===\n")
        print(prompt)
        
        if args.save:
            save_prompt_to_file(prompt, args.file_path)
            
        if args.visualize:
            visualize_song(features, args.file_path if args.visualize else None)
            
    except Exception as e:
        print(f"Error analyzing song: {e}")
        import traceback
        traceback.print_exc()
