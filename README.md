# Summary Bot NG

> An intelligent Discord bot that generates comprehensive summaries of conversations using AI-powered analysis

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Discord](https://img.shields.io/badge/Discord-Bot-7289DA.svg)](https://discord.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991.svg)](https://openai.com)
[![Poetry](https://img.shields.io/badge/Poetry-Dependency%20Management-blue.svg)](https://python-poetry.org)

## 🎯 Overview

Summary Bot NG is an advanced Discord bot that transforms lengthy conversations into structured, actionable summaries. Using OpenAI's GPT-4, it intelligently filters content, preserves important context, and delivers clean, organized documentation perfect for teams, communities, and knowledge management.

## ✨ Key Features

### 🤖 AI-Powered Summarization
- **GPT-4 Integration**: Leverages OpenAI's most advanced language model
- **Smart Content Filtering**: Automatically removes noise and focuses on key points
- **Structured Output**: Generates summaries with H2 headers and nested bullet points
- **Context Preservation**: Maintains message links and important metadata

### 💬 Discord Integration
- **Slash Commands**: Interactive `/summarize` commands for manual summaries
- **Real-time Processing**: Instant summary generation on demand
- **Channel Flexibility**: Summarize specific channels or cross-channel conversations
- **Permission Management**: Granular control over who can use bot features

### 🔗 External Platform Support
- **REST API**: HTTP endpoints for external summary requests
- **Webhook Integration**: Configurable destinations for automated delivery
- **Multi-platform Export**: Direct integration with Confluence, Notion, GitHub Wiki
- **Format Options**: Support for HTML, Markdown, and custom formats

### ⚙️ Advanced Configuration
- **Channel Management**: Include/exclude specific channels from summaries
- **Custom Prompts**: Configurable AI prompt templates for different use cases
- **Content Control**: Filter by message types, users, or time ranges
- **Output Customization**: Tailored formatting for different audiences

## 🎪 Use Cases

### For Teams & Organizations
- **Meeting Documentation**: Convert Discord discussions into meeting notes
- **Knowledge Management**: Archive important conversations for future reference
- **Project Updates**: Generate status reports from development channels
- **Decision Tracking**: Document key decisions and rationale

### For Communities
- **Event Summaries**: Capture highlights from community events
- **Discussion Archival**: Preserve valuable community discussions
- **Moderation Support**: Track important conversations for review
- **Content Curation**: Extract key insights from active channels

### For Developers & Researchers
- **Code Review Summaries**: Document technical discussions and decisions
- **Research Documentation**: Organize findings and insights
- **Issue Tracking**: Summarize bug reports and feature discussions
- **Learning Resources**: Create study materials from educational conversations

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Discord Bot Token
- OpenAI API Key
- Poetry for dependency management

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd summarybot-ng

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the bot
poetry run python src/main.py
```

### Discord Setup
1. Create a Discord application at https://discord.com/developers/applications
2. Generate a bot token and add it to your `.env` file
3. Invite the bot to your server with appropriate permissions
4. Use `/summarize` to start generating summaries

## 📚 Documentation

- **[Getting Started](docs/getting-started.md)** - Complete installation and setup guide
- **[API Reference](docs/api-reference.md)** - REST endpoints and webhook configuration
- **[Configuration](docs/configuration.md)** - Environment variables and customization options
- **[Examples](docs/examples.md)** - Usage examples and common patterns
- **[Development](docs/development.md)** - Contributing guidelines and development setup
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## 🛠️ Technical Stack

- **Language**: Python 3.8+
- **Framework**: discord.py for Discord integration
- **AI**: OpenAI GPT-4 API
- **Dependencies**: Poetry for package management
- **Configuration**: Environment variables and YAML config files
- **Web Server**: FastAPI for webhook endpoints (default port 5000)

## 🔮 Roadmap

### Near Term
- [ ] Multi-language support for international communities
- [ ] Sentiment analysis integration for conversation insights
- [ ] Topic categorization for better organization
- [ ] Advanced filtering by user roles and permissions

### Future Enhancements
- [ ] Slack integration for cross-platform summarization
- [ ] GitHub integration for automatic issue and PR summaries
- [ ] Analytics dashboard for usage insights
- [ ] Custom AI model training for domain-specific summaries
- [ ] Voice channel transcription and summarization

## 🤝 Contributing

We welcome contributions! Please see our [Development Guide](docs/development.md) for details on:

- Setting up the development environment
- Code style and testing guidelines
- Submitting pull requests
- Reporting issues and feature requests

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋 Support

- **Documentation**: Check our [comprehensive docs](docs/)
- **Issues**: Report bugs or request features via GitHub Issues
- **Community**: Join our Discord server for support and discussions

---

Built with ❤️ for better communication and knowledge management