import os
import edge_tts

async def generate_podcast_audio(script_turns, output_file_path):
    """
    Synthesizes speech for each script turn using edge-tts and concatenates
    the audio files into a single output MP3.
    """
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    temp_files = []
    
    # Using high-quality Edge-TTS neural voices
    emma_voice = "en-US-EmmaNeural"
    andrew_voice = "en-US-AndrewNeural"
    
    try:
        # Generate individual audio turns
        for i, turn in enumerate(script_turns):
            speaker = turn.get("speaker", "Emma")
            text = turn.get("text", "")
            
            # Select voice based on speaker
            voice = emma_voice if speaker.lower() == "emma" else andrew_voice
            
            # Temp file path
            temp_path = f"{output_file_path}_temp_{i}.mp3"
            
            # Call Edge TTS Communicate
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(temp_path)
            temp_files.append(temp_path)
            
        # Concatenate MP3 binary streams
        with open(output_file_path, "wb") as outfile:
            for temp_path in temp_files:
                if os.path.exists(temp_path):
                    with open(temp_path, "rb") as infile:
                        outfile.write(infile.read())
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        print(f"Error cleaning up temp file {temp_path}: {e}")
                        
        return True
    except Exception as e:
        print(f"Error in generate_podcast_audio: {e}")
        # Clean up temp files if anything fails
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
        raise e
