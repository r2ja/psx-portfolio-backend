"""Email service for portfolio alerts and updates."""

import os
from typing import List, Dict, Any
from datetime import datetime


class EmailService:
    """Handle email notifications via SMTP or Resend."""

    def __init__(self, api_key: str = None):
        """Initialize email service."""
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        # For now, just print emails (will integrate Resend later)
        self.mock_mode = not self.api_key

    def send_portfolio_update(
        self,
        to_email: str,
        portfolio_analysis: Dict[str, Any],
        alerts: List[Dict[str, Any]] = None
    ) -> bool:
        """
        Send daily portfolio update email.

        Args:
            to_email: Recipient email
            portfolio_analysis: Analysis from agent
            alerts: List of triggered alerts

        Returns:
            True if sent successfully
        """
        subject = f"📊 Your PSX Portfolio Update - {datetime.now().strftime('%B %d, %Y')}"

        # Build email body
        body = self._build_portfolio_email(portfolio_analysis, alerts)

        if self.mock_mode:
            print(f"\n{'='*60}")
            print(f"MOCK EMAIL TO: {to_email}")
            print(f"SUBJECT: {subject}")
            print(f"{'='*60}")
            print(body)
            print(f"{'='*60}\n")
            return True

        # TODO: Integrate with Resend API
        # resend.Emails.send({
        #     "from": "alerts@psx-portfolio.com",
        #     "to": to_email,
        #     "subject": subject,
        #     "html": body
        # })

        return True

    def send_alert(
        self,
        to_email: str,
        alert_type: str,
        stock_data: Dict[str, Any]
    ) -> bool:
        """
        Send immediate alert when condition is triggered.

        Args:
            to_email: Recipient email
            alert_type: Type of alert (price_target, rsi_alert, etc.)
            stock_data: Current stock data

        Returns:
            True if sent successfully
        """
        subject = f"🚨 Alert: {stock_data.get('symbol', 'Stock')} - {alert_type}"

        body = self._build_alert_email(alert_type, stock_data)

        if self.mock_mode:
            print(f"\n{'='*60}")
            print(f"MOCK ALERT TO: {to_email}")
            print(f"SUBJECT: {subject}")
            print(f"{'='*60}")
            print(body)
            print(f"{'='*60}\n")
            return True

        # TODO: Integrate with Resend API
        return True

    def _build_portfolio_email(
        self,
        analysis: Dict[str, Any],
        alerts: List[Dict[str, Any]] = None
    ) -> str:
        """Build HTML email body for portfolio update."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
        .stock {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .profit {{ color: #16a34a; font-weight: bold; }}
        .loss {{ color: #dc2626; font-weight: bold; }}
        .alert {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Your PSX Portfolio Update</h1>
            <p>{datetime.now().strftime('%B %d, %Y')}</p>
        </div>

        <div class="content">
            <h2>Portfolio Analysis</h2>
            <p>{analysis.get('analysis', 'No analysis available')}</p>

            {"<h2>🚨 Alerts Triggered</h2>" + self._format_alerts(alerts) if alerts else ""}
        </div>

        <div class="footer" style="margin-top: 30px; text-align: center; color: #666; font-size: 12px;">
            <p>PSX Portfolio Manager • Powered by AI</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_alert_email(self, alert_type: str, stock_data: Dict[str, Any]) -> str:
        """Build HTML email body for alert."""
        symbol = stock_data.get('symbol', 'Unknown')
        price = stock_data.get('price', 0)
        change = stock_data.get('change_percent', 0)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .alert-box {{ background: #fee2e2; border: 2px solid #dc2626; padding: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="alert-box">
            <h1>🚨 Alert: {alert_type}</h1>
            <h2>{symbol}</h2>
            <p><strong>Current Price:</strong> {price} PKR</p>
            <p><strong>Change:</strong> {change:+.2f}%</p>
            <p>{stock_data.get('message', 'Alert condition triggered')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _format_alerts(self, alerts: List[Dict[str, Any]]) -> str:
        """Format alerts for email."""
        if not alerts:
            return ""

        html = "<div>"
        for alert in alerts:
            html += f"""
            <div class="alert">
                <strong>{alert.get('symbol', 'Stock')}</strong>: {alert.get('message', 'Alert triggered')}
            </div>
            """
        html += "</div>"
        return html


# Singleton
_email_service = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
