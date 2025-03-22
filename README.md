
# Feelix: Emotional Expression Through Light and Sound

## Description

Feelix is an innovative human-computer interaction system that combines emotion detection, visual feedback, and audio response to create an engaging, emotionally aware computing experience. Using advanced natural language processing and custom lighting hardware, Feelix analyzes text input for emotional content and expresses the detected emotions through synchronized light displays and audio feedback.

## How It Works

The system operates through three main components:

1. Emotion Detection:
   The program uses the distilRoBERTa model fine-tuned for emotion detection, capable of identifying seven distinct emotional states: anger, disgust, fear, joy, neutral, sadness, and surprise. This model processes text input in real-time to determine the prevalent emotion.

2. Visual Expression:
   Feelix controls Busylight USB devices to create visual representations of detected emotions. Each emotion corresponds to specific light colors and patterns:
   - Anger: Red
   - Joy: Pink
   - Sadness: Cyan
   - Surprise: Orange 
   - Fear: Purple
   - Disgust: Green
   - Neutral: Soft white

3. Audio Feedback:
   The system provides audio feedback through text-to-speech capabilities, offering both offline (pyttsx3) and online (Google Text-to-Speech) options for vocalization of the analyzed text.

## Requirements

### Hardware Requirements
- One or more Kuando Busylight devices (supported models: Alpha, UC, Omega)
- USB ports for device connection
- Audio output capability (speakers or headphones)

### Software Dependencies
```bash
pip install -r requirements.txt
```

Required Python packages:
- torch
- transformers
- numpy
- pygame
- pyttsx3
- gTTS
- hid
- pandas
- requests

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/feelix.git
cd feelix
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Connect Busylight device(s) to available USB ports

4. Run the program:
```bash
python Feelix.py
```

## Usage

1. Launch the application
2. Type text into the input box
3. Press Enter to analyze the emotional content
4. Observe the light display and listen to the audio feedback
5. Press ESC to exit

## Configuration

The `busylight_commands.py` file contains customizable settings for:
- Color mappings
- Audio parameters
- Emotion-to-feedback mappings
- Device communication protocols

## Known Issues and Limitations

- Requires device drivers for Busylight hardware
- May experience slight latency with online text-to-speech
- Limited to seven basic emotions
- USB connection required (no wireless support currently)

## Contributing

We welcome contributions! Please see our contributing guidelines for details on:
- Code style
- Testing requirements
- Pull request process
- Development environment setup

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.

## Acknowledgments

- Kuando Busylight for hardware support
- Hugging Face for the emotion detection model
- The open-source community for various Python libraries

## Future Development

Planned features include:
- Wireless device support
- Extended emotion detection
- Custom animation patterns
- Enterprise integration capabilities
- Mobile application control
- Multi-device synchronization
- Advanced analytics dashboard

## Support

For support, please:
1. Check the FAQ section
2. Review existing issues on GitHub
3. Submit new issues with detailed descriptions
4. Contact the development team

## Version History

Current Version: 1.0.0
- Initial release with basic emotion detection and feedback
- Support for multiple Busylight devices
- Basic audio feedback system
- Simple user interface

For more information, contact: [your-email@example.com]


![Busylight-Competition-Theodore-Stabile-2](https://github.com/user-attachments/assets/cc59fb29-df2d-4e28-adaa-d78182e1eb0a)


