# Google Ads API v20 MCP Server

A comprehensive Model Context Protocol (MCP) server that provides full access to Google Ads API v20 functionality. This server enables AI assistants to perform any Google Ads operation through natural language commands.

## Features

### Complete API Coverage
- **Account Management**: List accounts, get account info, view hierarchy
- **Campaign Management**: Create, update, pause/resume campaigns with all v20 features
- **Ad Group Management**: Full CRUD operations for ad groups
- **Ad Creation**: Responsive search ads, expanded text ads, and more
- **Asset Management**: Upload and manage images, text assets
- **Budget Management**: Create and manage shared budgets
- **Keyword Management**: Add keywords, negative keywords (including Performance Max campaign-level negatives)
- **Reporting & Analytics**: Custom GAQL queries, performance reports, search terms
- **Advanced Features**: Recommendations, change history, experiments

### Intelligent Features
- **Automatic Retry Logic**: Handles transient errors with exponential backoff
- **Error Documentation**: Links to official Google Ads API error documentation
- **Partial Failure Handling**: Continues processing when some operations fail
- **Token Auto-Refresh**: Automatically refreshes OAuth tokens
- **Self-Rewriting**: Can look up documentation and retry failed operations

## Installation

```bash
# Install with pip
pip install -e .

# Or install dependencies directly
pip install mcp google-ads pydantic httpx tenacity python-dotenv beautifulsoup4 structlog
```

## Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# OAuth2 Authentication
GOOGLE_ADS_CLIENT_ID=your_client_id
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token

# OR Service Account Authentication
GOOGLE_ADS_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
GOOGLE_ADS_IMPERSONATED_EMAIL=user@example.com  # Optional

# Required for all auth methods
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890  # Manager account ID if applicable
```

### Configuration File

Alternatively, create a config file at `~/.config/google-ads-mcp/config.json`:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "refresh_token": "your_refresh_token",
  "developer_token": "your_developer_token",
  "login_customer_id": "1234567890"
}
```

## MCP Configuration

Add to your Claude Desktop config (`~/.config/claude/mcp.json`):

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "python",
      "args": ["-m", "google-ads-mcp"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "your_token",
        "GOOGLE_ADS_CLIENT_ID": "your_client_id",
        "GOOGLE_ADS_CLIENT_SECRET": "your_secret",
        "GOOGLE_ADS_REFRESH_TOKEN": "your_refresh_token"
      }
    }
  }
}
```

## Usage Examples

### Basic Operations

```
# List all accounts
Use the list_accounts tool

# Create a campaign
Use create_campaign with customer_id="1234567890", name="Summer Sale 2025", 
budget_amount=100.0, campaign_type="SEARCH"

# Get campaign performance
Use get_campaign_performance with customer_id="1234567890", date_range="LAST_30_DAYS"
```

### Advanced Queries

```
# Run custom GAQL query
Use run_gaql_query with query:
SELECT campaign.name, metrics.clicks, metrics.conversions
FROM campaign
WHERE metrics.impressions > 1000
  AND segments.date DURING LAST_7_DAYS
ORDER BY metrics.clicks DESC
```

### Performance Max Features (v20)

```
# Add negative keywords to Performance Max campaign
Use add_negative_keywords with customer_id="1234567890", 
campaign_id="123", keywords=["cheap", "discount", "free"]
```

## Error Handling

The server provides detailed error information:
- Error type and code
- Human-readable message
- Whether the error is retryable
- Link to official documentation
- Suggestions for fixing common errors

## Development

### Running Tests
```bash
pytest tests/
```

### Adding New Tools

1. Add tool definition to `_register_tools()` in `tools.py`
2. Implement the handler method
3. Update documentation

### Debugging
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python -m google-ads-mcp
```

## Security Notes

- Never commit credentials to version control
- Use service accounts for production environments
- Enable 2FA on Google Ads accounts
- Regularly rotate refresh tokens
- Monitor API usage and set alerts

## API Version Support

This server is built for Google Ads API v20 (released June 2025) and includes:
- Campaign-level negative keywords for Performance Max
- Enhanced Demand Gen reporting with channel segmentation
- Platform comparable conversions
- All v20-specific features and improvements

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues and questions:
- Check the [Google Ads API documentation](https://developers.google.com/google-ads/api/docs/start)
- Review error messages and documentation links
- Open an issue on GitHub