#!/usr/bin/env python3
"""
Script to fetch and summarize stock market messages from a specific user in a Discord channel
"""
import os
import sys
import json
import yaml
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import argparse
import time
import tempfile
from io import BytesIO

# OCR for image text extraction
try:
    import easyocr
    from PIL import Image
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: easyocr or Pillow not installed. OCR disabled. Install with: pip install easyocr Pillow")

# PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: reportlab not installed. PDF generation disabled. Install with: pip install reportlab")

class DiscordMessageFetcher:
    """Fetch messages from Discord channels"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        # Initialize OCR reader if available
        self.ocr_reader = None
        if OCR_AVAILABLE:
            try:
                print("Initializing OCR reader (this may take a moment on first run)...")
                self.ocr_reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)  # Support English and Chinese
                print("OCR reader initialized successfully")
            except Exception as e:
                print(f"Warning: Failed to initialize OCR reader: {e}")
                self.ocr_reader = None
    
    def extract_text_from_image(self, image_url: str) -> str:
        """
        Extract text from an image using OCR
        
        Args:
            image_url: URL of the image to process
        
        Returns:
            Extracted text from the image
        """
        if not OCR_AVAILABLE or not self.ocr_reader:
            print(f"[OCR] OCR not available or reader not initialized")
            return ""
        
        try:
            # Download image
            print(f"[OCR] Downloading image from: {image_url[:100]}...")
            response = requests.get(image_url, headers={"Authorization": self.token}, timeout=30)
            response.raise_for_status()
            
            # Load image and convert to numpy array (easyocr requires numpy array, not PIL Image)
            image = Image.open(BytesIO(response.content))
            print(f"[OCR] Image loaded, size: {image.size}")
            
            # Convert PIL Image to numpy array
            image_array = np.array(image)
            print(f"[OCR] Image converted to numpy array, shape: {image_array.shape}")
            
            # Extract text using OCR (pass numpy array or image bytes)
            print(f"[OCR] Running OCR...")
            # easyocr can accept numpy array directly
            results = self.ocr_reader.readtext(image_array)
            print(f"[OCR] OCR found {len(results)} text regions")
            
            # Combine all detected text with better formatting
            extracted_lines = []
            for result in results:
                text = result[1]
                confidence = result[2] if len(result) > 2 else 0
                if confidence > 0.3:  # Filter low confidence results
                    extracted_lines.append(text)
                    print(f"[OCR] Text: '{text}' (confidence: {confidence:.2f})")
            
            extracted_text = " ".join(extracted_lines)
            
            if extracted_text:
                print(f"[OCR] Full extracted text: {extracted_text}")
            else:
                print(f"[OCR] No text extracted (all results below confidence threshold)")
            
            return extracted_text
        except Exception as e:
            print(f"[OCR] Error extracting text from image {image_url}: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def fetch_messages(self, channel_id: str, limit: int = 100, before: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch messages from a channel
        
        Args:
            channel_id: Discord channel ID
            limit: Maximum number of messages to fetch (1-100)
            before: Message ID to fetch messages before this ID (for pagination)
        
        Returns:
            List of message objects
        """
        url = f"{self.base_url}/channels/{channel_id}/messages"
        params = {"limit": min(limit, 100)}
        
        if before:
            params["before"] = before
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching messages: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return []
    
    def fetch_all_user_messages(self, channel_id: str, username: str, max_messages: int = 1000, last_24_hours: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch all messages from a specific user in a channel
        
        Args:
            channel_id: Discord channel ID
            username: Username to filter by (case-insensitive)
            max_messages: Maximum total messages to fetch
            last_24_hours: If True, only fetch messages from last 24 hours
        
        Returns:
            List of messages from the specified user
        """
        all_messages = []
        user_messages = []
        before = None
        username_lower = username.lower()
        
        # Calculate 24 hours ago timestamp if needed
        cutoff_time = None
        if last_24_hours:
            cutoff_time = datetime.now() - timedelta(hours=24)
            print(f"Fetching messages from last 24 hours (since {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})...")
        else:
            print(f"Fetching messages from user '{username}' in channel {channel_id}...")
        
        while len(all_messages) < max_messages:
            # Fetch a batch of messages
            messages = self.fetch_messages(channel_id, limit=100, before=before)
            
            if not messages:
                break
            
            # Filter messages from the target user and time range
            for msg in messages:
                # Check time filter first (more efficient)
                if last_24_hours and cutoff_time:
                    try:
                        msg_timestamp = datetime.fromisoformat(msg.get("timestamp", "").replace('Z', '+00:00'))
                        # Convert to local time for comparison
                        if msg_timestamp.tzinfo:
                            msg_timestamp = msg_timestamp.replace(tzinfo=None)
                        if msg_timestamp < cutoff_time:
                            # Messages are ordered newest first, so if we hit old messages, we're done
                            return user_messages
                    except:
                        pass  # Skip time check if timestamp parsing fails
                
                # Check user filter
                msg_author = msg.get("author", {}).get("username", "").lower()
                if msg_author == username_lower:
                    user_messages.append(msg)
            
            all_messages.extend(messages)
            
            # Check if we've fetched all available messages
            if len(messages) < 100:
                break
            
            # Set before to the oldest message ID for next iteration
            before = messages[-1]["id"]
            
            if not last_24_hours:
                print(f"Fetched {len(all_messages)} total messages, found {len(user_messages)} from {username}")
        
        print(f"\nTotal messages found from {username}: {len(user_messages)}")
        return user_messages
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information"""
        url = f"{self.base_url}/channels/{channel_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching channel info: {e}")
            return None
    
    def generate_pdf(self, content: str, filename: str = None) -> Optional[BytesIO]:
        """
        Generate a PDF file from text content
        
        Args:
            content: Text content to convert to PDF
            filename: Optional filename (not used, returns BytesIO)
        
        Returns:
            BytesIO object containing PDF data, or None if PDF generation fails
        """
        if not PDF_AVAILABLE:
            print("Error: reportlab not installed. Cannot generate PDF.")
            return None
        
        try:
            # Create PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4,
                                  rightMargin=72, leftMargin=72,
                                  topMargin=72, bottomMargin=18)
            
            # Container for the 'Flowable' objects
            elements = []
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor='#000000',
                spaceAfter=12,
                alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor='#000000',
                spaceAfter=10,
                spaceBefore=12
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor='#000000',
                spaceAfter=6,
                leading=14
            )
            
            # Split content into lines and process
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    elements.append(Spacer(1, 6))
                    continue
                
                # Check if it's a heading (starts with # or **)
                if line.startswith('###') or line.startswith('##') or line.startswith('#'):
                    # Remove markdown formatting
                    clean_line = line.lstrip('#').strip()
                    if clean_line.startswith('**') and clean_line.endswith('**'):
                        clean_line = clean_line[2:-2]
                    elements.append(Paragraph(clean_line, heading_style))
                    elements.append(Spacer(1, 6))
                elif line.startswith('**') and line.endswith('**'):
                    # Bold text
                    clean_line = line[2:-2]
                    bold_style = ParagraphStyle(
                        'Bold',
                        parent=normal_style,
                        fontName='Helvetica-Bold'
                    )
                    elements.append(Paragraph(clean_line, bold_style))
                elif line.startswith('*') and line.endswith('*'):
                    # Italic or bullet point
                    clean_line = line.strip('*').strip()
                    elements.append(Paragraph(f"• {clean_line}", normal_style))
                elif line.startswith('=') and len(line) > 10:
                    # Separator line
                    elements.append(Spacer(1, 12))
                else:
                    # Normal text
                    # Escape special characters for ReportLab
                    clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    elements.append(Paragraph(clean_line, normal_style))
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def send_message(self, channel_id: str, content: str, as_pdf: bool = False) -> bool:
        """
        Send a message to a Discord channel
        
        Args:
            channel_id: Discord channel ID
            content: Message content
            as_pdf: If True, send as PDF file instead of text message
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/channels/{channel_id}/messages"
        
        if as_pdf:
            # Generate PDF and send as file
            pdf_buffer = self.generate_pdf(content)
            if not pdf_buffer:
                print("Failed to generate PDF, falling back to text message")
                return self.send_message(channel_id, content, as_pdf=False)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_{timestamp}.pdf"
            
            # Prepare multipart/form-data request
            files = {
                'file': (filename, pdf_buffer, 'application/pdf')
            }
            data = {
                'content': f'📄 **AI Summary Report**\nGenerated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            }
            
            try:
                # Remove Content-Type header for multipart/form-data
                headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
                response = requests.post(url, headers=headers, data=data, files=files)
                response.raise_for_status()
                print(f"✓ PDF sent successfully: {filename}")
                return True
            except requests.exceptions.RequestException as e:
                print(f"Error sending PDF to Discord: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response: {e.response.text[:200]}")
                return False
        else:
            # Original text message sending logic
            # Discord has a 2000 character limit per message
            # Split into multiple messages if needed
            max_length = 1900  # Leave some buffer
            
            if len(content) <= max_length:
                payload = {"content": content}
                try:
                    response = requests.post(url, headers=self.headers, json=payload)
                    response.raise_for_status()
                    return True
                except requests.exceptions.RequestException as e:
                    print(f"Error sending message to Discord: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"Response: {e.response.text[:200]}")
                    return False
            else:
                # Split into chunks
                chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
                success = True
                for i, chunk in enumerate(chunks):
                    chunk_header = f"**消息 {i+1}/{len(chunks)}**\n\n" if len(chunks) > 1 else ""
                    payload = {"content": chunk_header + chunk}
                    try:
                        response = requests.post(url, headers=self.headers, json=payload)
                        response.raise_for_status()
                        time.sleep(0.5)  # Rate limit protection
                    except requests.exceptions.RequestException as e:
                        print(f"Error sending message chunk {i+1}: {e}")
                        success = False
                return success


class StockMarketAnalyzer:
    """Analyze and summarize stock market messages"""
    
    def __init__(self):
        # Keywords related to stock market
        self.stock_keywords = [
            "stock", "stocks", "equity", "equities",
            "ticker", "tickers", "symbol", "symbols",
            "buy", "sell", "long", "short", "position",
            "bullish", "bearish", "bull", "bear",
            "price", "target", "entry", "exit", "stop loss",
            "earnings", "revenue", "profit", "loss",
            "market", "trading", "trade", "trader",
            "crypto", "bitcoin", "btc", "eth", "ethereum",
            "forex", "fx", "currency", "currencies",
            "option", "options", "call", "put",
            "dividend", "yield", "pe ratio", "valuation",
            "ipo", "merger", "acquisition", "split"
        ]
    
    def is_stock_related(self, content: str) -> bool:
        """
        Check if message content is related to stock market
        Includes messages with stock keywords OR stock tickers
        """
        content_lower = content.lower()
        
        # Check for stock keywords
        if any(keyword in content_lower for keyword in self.stock_keywords):
            return True
        
        # Check for stock tickers (e.g., $AAPL, TSLA, QQQ, MSTR)
        # This ensures messages with tickers are included even without keywords
        tickers = self.extract_tickers(content)
        if tickers:
            return True
        
        # Check for common trading patterns (numbers with p/c for options, percentages, etc.)
        import re
        # Options patterns: "166p", "609p", "166c", etc.
        if re.search(r'\b\d+[pc]\b', content, re.IGNORECASE):
            return True
        # Percentage patterns: "+90%", "gain 60%", etc.
        if re.search(r'[\+\-]?\d+%', content):
            return True
        # Price patterns: "2.89", "1.96", "成本0.96", etc.
        if re.search(r'(?:成本|price|@|at)\s*[\d,]+\.?\d*', content, re.IGNORECASE):
            return True
        
        return False
    
    def extract_tickers(self, content: str) -> List[str]:
        """Extract potential stock tickers from message (simple pattern matching)"""
        import re
        # Look for patterns like $AAPL, AAPL, or ticker symbols
        ticker_patterns = [
            r'\$([A-Z]{1,5})\b',  # $AAPL format
            r'\b([A-Z]{1,5})\b',  # Standalone uppercase (2-5 chars)
        ]
        tickers = set()
        for pattern in ticker_patterns:
            matches = re.findall(pattern, content)
            tickers.update(matches)
        return list(tickers)
    
    def extract_orders(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract trading orders from message content
        Looks for buy/sell orders with quantities, prices, tickers
        """
        import re
        orders = []
        content_lower = content.lower()
        
        # Patterns for order extraction - More flexible patterns to match various formats
        # Buy/Sell patterns: "buy 100 TSLA at $250", "sold 50 shares", "long AAPL", "买入100股", etc.
        # Also supports options: "mstr weekly 166p 2.89", "qqq 609p 1.96", etc.
        order_patterns = [
            # Options patterns: "mstr weekly 166p 2.89", "qqq 609p 1.96"
            (r'([A-Z]{1,5})\s+(?:weekly|monthly|daily)?\s*(\d+)([pc])\s+([\d,]+\.?\d*)', 'buy'),  # Options format
            (r'([A-Z]{1,5})\s*(\d+)([pc])\s+([\d,]+\.?\d*)', 'buy'),  # Simplified options
            # Buy patterns - quantity first
            (r'(?:buy|bought|long|entered|entry|买入|做多|加了一笔|bet)\s+(?:@|at|@|在)?\s*(\d+)\s*(?:shares?|contracts?|股|手|份)?\s*(?:of\s+)?([A-Z]{1,5})\s*(?:@|at|@|在)?\s*\$?([\d,]+\.?\d*)', 'buy'),
            # Buy patterns - ticker first
            (r'(?:buy|bought|long|entered|entry|买入|做多|加了一笔|bet)\s+([A-Z]{1,5})\s+(?:@|at|@|在)?\s*\$?([\d,]+\.?\d*)\s*(?:x|×|乘)?\s*(\d+)', 'buy'),
            # Buy patterns - simplified (just ticker and price, assume quantity 1)
            (r'(?:buy|bought|long|entered|entry|买入|做多|加了一笔|bet)\s+([A-Z]{1,5})\s+(?:@|at|@|在)?\s*\$?([\d,]+\.?\d*)', 'buy'),
            # Sell patterns - quantity first
            (r'(?:sell|sold|short|exit|closed|cover|卖出|做空|平仓|切掉|切|卖出部份)\s+(?:@|at|@|在)?\s*(\d+)\s*(?:shares?|contracts?|股|手|份)?\s*(?:of\s+)?([A-Z]{1,5})\s*(?:@|at|@|在)?\s*\$?([\d,]+\.?\d*)', 'sell'),
            # Sell patterns - ticker first
            (r'(?:sell|sold|short|exit|closed|cover|卖出|做空|平仓|切掉|切|卖出部份)\s+([A-Z]{1,5})\s+(?:@|at|@|在)?\s*\$?([\d,]+\.?\d*)\s*(?:x|×|乘)?\s*(\d+)', 'sell'),
            # Sell patterns - simplified (just ticker and price, assume quantity 1)
            (r'(?:sell|sold|short|exit|closed|cover|卖出|做空|平仓|切掉|切|卖出部份)\s+([A-Z]{1,5})\s+(?:@|at|@|在)?\s*\$?([\d,]+\.?\d*)', 'sell'),
            # Position updates: "现1.78", "现成本0.96", "成本负了"
            (r'([A-Z]{1,5}).*?(?:现|current|成本|cost)\s*([\+\-]?[\d,]+\.?\d*)', 'position'),
            # Discord trading card format: "IONQ PUT" with "0.36" and "200"
            # Pattern: TICKER PUT/CALL followed by price and quantity (flexible spacing)
            # Match: "IONQ PUT 0.36 200" or "IONQ PUT\n0.36\n200" or "IONQ PUT 0.36 200张"
            (r'([A-Z]{1,5})\s+(?:PUT|CALL|put|call)\s+(?:[\d\s]+)?\s*([\d,]+\.?\d*)\s*(?:[\d\s]+)?\s*(\d+)', 'buy'),
            # More flexible: "IONQ PUT" anywhere, then price, then quantity (with optional text between)
            (r'([A-Z]{1,5})\s+(?:PUT|CALL|put|call).*?([\d,]+\.?\d*).*?(\d+)\s*(?:张|contracts?|shares?)?', 'buy'),
            # Even more flexible: ticker, PUT/CALL, then any numbers (price and quantity)
            (r'([A-Z]{1,5})\s+(?:PUT|CALL|put|call).*?([\d,]+\.?\d+).*?(\d+)', 'buy'),
            # Chinese trading card: "买入" + ticker + price + quantity
            (r'(?:买入|卖出)\s*([A-Z]{1,5})\s*(?:PUT|CALL|put|call)?.*?([\d,]+\.?\d*).*?(\d+)\s*(?:张|contracts?|shares?)?', 'buy'),
            # Format: "全部成交" + ticker + price + quantity
            (r'(?:全部成交|部分成交|成交)\s*([A-Z]{1,5})\s*(?:PUT|CALL|put|call)?.*?([\d,]+\.?\d*).*?(\d+)', 'buy'),
            # Standalone format: Just "IONQ PUT" followed by price and quantity in any order
            (r'([A-Z]{1,5})\s+(?:PUT|CALL|put|call).*?(\d+\.\d+).*?(\d+)', 'buy'),
            (r'([A-Z]{1,5})\s+(?:PUT|CALL|put|call).*?(\d+).*?(\d+\.\d+)', 'buy'),
            # OCR-extracted format: May have spaces or special characters
            # "IONQ PUT 0.36 200" or "IONQPUT 0.36 200" or "IONQ PUT 0 36 200"
            (r'([A-Z]{1,5})\s*(?:PUT|CALL|put|call).*?([\d,]+\.?\d*).*?(\d+)\s*(?:张|contracts?|shares?)?', 'buy'),
            # More flexible: Any ticker followed by PUT/CALL and numbers
            (r'\b([A-Z]{1,5})\s*(?:PUT|CALL|put|call)\b.*?([\d,]+\.?\d+).*?(\d+)', 'buy'),
            (r'\b([A-Z]{1,5})\s*(?:PUT|CALL|put|call)\b.*?(\d+).*?([\d,]+\.?\d+)', 'buy'),
        ]
        
        for pattern, order_type in order_patterns:
            # Try both original content and a cleaned version (remove extra spaces, normalize)
            content_cleaned = re.sub(r'\s+', ' ', content)  # Normalize whitespace
            matches = re.finditer(pattern, content_cleaned, re.IGNORECASE)  # Use cleaned content for better matching
            for match in matches:
                groups = match.groups()
                try:
                    if len(groups) == 4 and order_type == 'buy':
                        # Check if this is Discord trading card format: "IONQ PUT 0.36 200"
                        # Groups: ticker, price, quantity
                        if groups[1].replace('.', '').replace(',', '').isdigit() and groups[2].isdigit():
                            # Format: ticker price quantity (Discord card)
                            ticker = groups[0].upper()
                            price = float(groups[1].replace(',', '').replace('$', ''))
                            quantity = int(groups[2])
                            # Check if ticker contains PUT/CALL info in the original match
                            match_text = match.group(0).upper()
                            if 'PUT' in match_text:
                                ticker = f"{ticker} PUT"
                            elif 'CALL' in match_text:
                                ticker = f"{ticker} CALL"
                        else:
                            # Options format: ticker strike p/c price (e.g., "mstr weekly 166p 2.89")
                            ticker = groups[0].upper()
                            strike = groups[1]
                            option_type = groups[2].upper()  # 'P' or 'C'
                            price = float(groups[3].replace(',', '').replace('$', ''))
                            quantity = 1  # Default for options
                            ticker = f"{ticker} {strike}{option_type}"  # Format as "MSTR 166P"
                    elif len(groups) == 3:
                        # Three groups: could be various formats
                        # Check if this is Discord card format: ticker PUT/CALL price quantity
                        match_text = match.group(0).upper()
                        if 'PUT' in match_text or 'CALL' in match_text:
                            # Discord card format: "IONQ PUT 0.36 200"
                            # Groups: ticker, price, quantity OR ticker, quantity, price
                            ticker = groups[0].upper()
                            
                            # Determine which is price and which is quantity
                            # Price usually has decimal point, quantity is usually integer
                            if '.' in str(groups[1]) or '.' in str(groups[2]):
                                # One has decimal (price), one is integer (quantity)
                                if '.' in str(groups[1]):
                                    price = float(str(groups[1]).replace(',', '').replace('$', ''))
                                    quantity = int(str(groups[2]).replace(',', ''))
                                else:
                                    price = float(str(groups[2]).replace(',', '').replace('$', ''))
                                    quantity = int(str(groups[1]).replace(',', ''))
                            else:
                                # Both might be integers, assume first numeric is price if small, second is quantity
                                val1 = float(str(groups[1]).replace(',', '').replace('$', ''))
                                val2 = float(str(groups[2]).replace(',', '').replace('$', ''))
                                # If one is much larger, it's likely quantity
                                if val2 > val1 * 10:
                                    price = val1
                                    quantity = int(val2)
                                elif val1 > val2 * 10:
                                    price = val2
                                    quantity = int(val1)
                                else:
                                    # Both similar, assume first is price, second is quantity
                                    price = val1
                                    quantity = int(val2)
                            
                            # Add PUT/CALL to ticker
                            if 'PUT' in match_text:
                                ticker = f"{ticker} PUT"
                            elif 'CALL' in match_text:
                                ticker = f"{ticker} CALL"
                        elif groups[0].isdigit():
                            # Format: quantity ticker price
                            quantity = int(groups[0])
                            ticker = groups[1].upper()
                            price = float(groups[2].replace(',', '').replace('$', ''))
                        elif groups[2].isdigit():
                            # Format: ticker price quantity
                            ticker = groups[0].upper()
                            price = float(groups[1].replace(',', '').replace('$', ''))
                            quantity = int(groups[2])
                        else:
                            # Format: ticker price (no quantity, assume 1)
                            ticker = groups[0].upper()
                            price = float(groups[1].replace(',', '').replace('$', ''))
                            quantity = 1
                    elif len(groups) == 2:
                        if order_type == 'position':
                            # Position update: ticker and current price/cost
                            ticker = groups[0].upper()
                            price = float(groups[1].replace(',', '').replace('$', '').replace('+', ''))
                            quantity = 0  # Position update, no quantity
                            order_type = 'position'
                        else:
                            # Two groups: ticker and price (simplified format, assume quantity 1)
                            ticker = groups[0].upper()
                            price = float(groups[1].replace(',', '').replace('$', ''))
                            quantity = 1
                    else:
                        continue
                    
                    # Validate extracted data
                    if ticker and price > 0:
                        if order_type == 'position':
                            orders.append({
                                'type': 'position',
                                'ticker': ticker,
                                'price': price,
                                'quantity': quantity,
                                'text': match.group(0)
                            })
                        else:
                            if quantity > 0:
                                order_entry = {
                                    'type': order_type,
                                    'ticker': ticker,
                                    'quantity': quantity,
                                    'price': price,
                                    'text': match.group(0)
                                }
                                orders.append(order_entry)
                                # Debug output to help troubleshoot
                                print(f"[DEBUG] Extracted order: {order_entry['type']} {order_entry['quantity']} {order_entry['ticker']} @ ${order_entry['price']:.2f} (from: {order_entry['text'][:50]}...)")
                except (ValueError, IndexError, AttributeError):
                    continue
        
        return orders
    
    def extract_pnl(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract profit/loss information from message content
        Looks for P/L, gain/loss, profit/loss mentions
        """
        import re
        pnl_list = []
        content_lower = content.lower()
        
        # Patterns for P/L extraction - Support various formats including Chinese
        pnl_patterns = [
            # "P/L: +$500", "profit: $1000", "loss: -$200"
            (r'(?:p/l|pnl|profit|loss|gain|return|盈亏|盈利|亏损)\s*[:\-]?\s*([\+\-]?\$?[\d,]+\.?\d*)', None),
            # "+$500", "-$200", "+5%", "-3%", "+90%", "gain 60%"
            (r'([\+\-]\$?[\d,]+\.?\d*(?:\s*%|percent)?)', None),
            (r'(?:gain|gained|盈利|赚)\s+([\+\-]?\d+\.?\d*(?:\s*%|percent)?)', 'profit'),
            # "made $500", "lost $200", "成本负了" (negative cost = profit)
            (r'(?:made|earned|gained|profit|won|赚|盈利)\s+([\+\-]?\$?[\d,]+\.?\d*)', 'profit'),
            (r'(?:lost|losing|loss|亏|亏损)\s+([\+\-]?\$?[\d,]+\.?\d*)', 'loss'),
            # Chinese patterns: "成本负了" (cost is negative = profit)
            (r'成本\s*(?:负|negative|is\s*negative)', 'profit'),
            # Percentage gains: "+90%", "gain 60%"
            (r'[\+\-]?\d+\.?\d*\s*%', None),
        ]
        
        for pattern, pnl_type in pnl_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    # Special handling for "成本负了" (negative cost = profit)
                    match_text = match.group(0)
                    if '成本' in match_text and ('负' in match_text or 'negative' in match_text.lower()):
                        pnl_list.append({
                            'type': 'profit',
                            'value': 0,  # Special marker for negative cost
                            'text': match_text,
                            'note': 'Negative cost (成本负了)'
                        })
                        continue
                    
                    # Extract value from match
                    # Check if pattern has capturing groups
                    if match.lastindex is not None and match.lastindex >= 1:
                        value_str = match.group(1)
                    else:
                        # No capturing group, use the full match
                        value_str = match_text
                    
                    # Clean value string
                    is_percentage = '%' in value_str
                    value_str = value_str.replace('$', '').replace(',', '').replace('%', '').strip()
                    
                    if not value_str:
                        continue
                    
                    value = float(value_str)
                    
                    # If percentage, convert to a reasonable estimate (assume base of 100 for calculation)
                    # For example, "+90%" could mean 90% gain on some position
                    if is_percentage:
                        # Store as percentage, but also calculate estimated value
                        # We'll store the percentage and let AI interpret it
                        pnl_list.append({
                            'type': 'profit' if value >= 0 else 'loss',
                            'value': value,  # Store percentage as-is
                            'text': match_text,
                            'is_percentage': True
                        })
                    else:
                        # Determine type if not specified
                        if pnl_type is None:
                            pnl_type = 'profit' if value >= 0 else 'loss'
                        elif pnl_type == 'profit' and value < 0:
                            pnl_type = 'loss'
                        elif pnl_type == 'loss' and value > 0:
                            pnl_type = 'profit'
                        
                        pnl_list.append({
                            'type': pnl_type,
                            'value': value,
                            'text': match_text
                        })
                except (ValueError, IndexError, AttributeError):
                    continue
        
        return pnl_list
    
    def summarize_messages(self, messages: List[Dict[str, Any]], fetcher: Optional['DiscordMessageFetcher'] = None) -> Dict[str, Any]:
        """
        Summarize stock market messages
        
        Args:
            messages: List of message objects
        
        Returns:
            Summary dictionary
        """
        stock_messages = []
        all_tickers = set()
        message_dates = []
        all_orders = []
        all_pnl = []
        
        for msg in messages:
            content = msg.get("content", "")
            # Extract content from embeds (Discord rich content like trading order cards)
            embeds = msg.get("embeds", [])
            embed_texts = []
            for embed in embeds:
                # Extract title
                if "title" in embed:
                    embed_texts.append(embed["title"])
                # Extract description
                if "description" in embed:
                    embed_texts.append(embed["description"])
                # Extract fields (common in trading order cards)
                if "fields" in embed:
                    for field in embed["fields"]:
                        if "name" in field:
                            embed_texts.append(field["name"])
                        if "value" in field:
                            embed_texts.append(field["value"])
                # Extract footer
                if "footer" in embed and "text" in embed["footer"]:
                    embed_texts.append(embed["footer"]["text"])
                # Extract author
                if "author" in embed and "name" in embed["author"]:
                    embed_texts.append(embed["author"]["name"])
            
            # Combine embed content with message content
            if embed_texts:
                embed_content = " ".join(embed_texts)
                content = (content + " " + embed_content).strip()
                # Debug: Print embed content for troubleshooting
                if embed_texts:
                    print(f"[DEBUG] Extracted embed content: {embed_content[:200]}...")
            
            # Check if message has attachments (images) - these might contain P/L info
            has_attachments = len(msg.get("attachments", [])) > 0
            has_embeds = len(msg.get("embeds", [])) > 0
            
            # Extract text from image attachments using OCR
            image_texts = []
            if has_attachments and fetcher and OCR_AVAILABLE:
                attachments = msg.get("attachments", [])
                for attachment in attachments:
                    # Check if it's an image
                    content_type = attachment.get("content_type", "")
                    filename = attachment.get("filename", "")
                    if content_type.startswith("image/") or filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                        image_url = attachment.get("url", "")
                        if image_url:
                            print(f"[OCR] Processing image attachment: {filename}")
                            extracted_text = fetcher.extract_text_from_image(image_url)
                            if extracted_text:
                                image_texts.append(extracted_text)
                                # Add OCR text to content for order extraction
                                content += f" {extracted_text}"
                                print(f"[OCR] Extracted text added to content: {extracted_text[:200]}...")
                            else:
                                print(f"[OCR] No text extracted from image: {filename}")
            elif has_attachments and not OCR_AVAILABLE:
                print(f"[WARNING] Image attachment found but OCR is not available. Install: pip install easyocr Pillow")
            elif has_attachments and not fetcher:
                print(f"[WARNING] Image attachment found but fetcher is not available")
            
            # Include message if it's stock-related OR has attachments (images) OR has embeds (trading cards)
            # IMPORTANT: All messages with images are included regardless of content (no filtering)
            # Also include if OCR extracted text from images
            if has_attachments or self.is_stock_related(content) or (has_embeds and embed_texts) or image_texts:
                timestamp = msg.get("timestamp", "")
                message_entry = {
                    "content": content,
                    "timestamp": timestamp,
                    "id": msg.get("id", "")
                }
                
                # Mark if message has images
                if has_attachments:
                    message_entry["has_images"] = True
                    message_entry["image_count"] = len(msg.get("attachments", []))
                    if image_texts:
                        message_entry["ocr_extracted"] = True
                        message_entry["ocr_text"] = " ".join(image_texts)
                    else:
                        # Note if OCR is not available or failed
                        if not OCR_AVAILABLE:
                            content += " [包含图片附件，但OCR未启用]"
                        elif fetcher:
                            content += " [包含图片附件，OCR提取失败或图片中无文字]"
                        else:
                            content += " [包含图片附件，可能包含交易记录或盈亏信息]"
                
                stock_messages.append(message_entry)
                
                # Extract tickers
                tickers = self.extract_tickers(content)
                all_tickers.update(tickers)
                
                # Extract orders
                print(f"[DEBUG] Extracting orders from content: {content[:200]}...")
                orders = self.extract_orders(content)
                print(f"[DEBUG] Found {len(orders)} orders")
                for order in orders:
                    order['timestamp'] = timestamp
                    all_orders.append(order)
                    print(f"[DEBUG] Added order: {order}")
                
                # Extract P/L
                pnl = self.extract_pnl(content)
                for p in pnl:
                    p['timestamp'] = timestamp
                    all_pnl.append(p)
                
                # Parse timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    message_dates.append(dt)
                except:
                    pass
        
        # Generate summary
        summary = {
            "total_messages": len(messages),
            "stock_related_messages": len(stock_messages),
            "tickers_mentioned": sorted(list(all_tickers)),
            "orders": all_orders,
            "pnl": all_pnl,
            "date_range": None,
            "messages": stock_messages[:50]  # Keep first 50 for detailed review
        }
        
        if message_dates:
            summary["date_range"] = {
                "earliest": min(message_dates).isoformat(),
                "latest": max(message_dates).isoformat()
            }
        
        return summary
    
    def format_summary(self, summary: Dict[str, Any], username: str, channel_name: str = None, channel_names: List[str] = None) -> str:
        """Format summary as readable text"""
        output = []
        output.append("=" * 80)
        output.append(f"STOCK MARKET MESSAGE SUMMARY")
        output.append("=" * 80)
        output.append(f"User: {username}")
        if channel_names and len(channel_names) > 1:
            output.append(f"Channels: {', '.join(channel_names)}")
        elif channel_name:
            output.append(f"Channel: {channel_name}")
        output.append(f"Total Messages Analyzed: {summary['total_messages']}")
        output.append(f"Stock-Related Messages: {summary['stock_related_messages']}")
        
        if summary.get("tickers_mentioned"):
            output.append(f"\nTickers Mentioned ({len(summary['tickers_mentioned'])}):")
            output.append(", ".join(summary['tickers_mentioned']))
        
        if summary.get("date_range"):
            output.append(f"\nDate Range:")
            output.append(f"  Earliest: {summary['date_range']['earliest']}")
            output.append(f"  Latest: {summary['date_range']['latest']}")
        
        output.append("\n" + "=" * 80)
        output.append("KEY MESSAGES:")
        output.append("=" * 80)
        
        for i, msg in enumerate(summary.get("messages", [])[:20], 1):
            output.append(f"\n[{i}] {msg.get('timestamp', 'Unknown date')}")
            output.append(f"{msg.get('content', '')[:200]}...")
            if len(msg.get('content', '')) > 200:
                output.append("...")
        
        return "\n".join(output)


class AISummarizer:
    """AI-powered summarization using OpenAI or other AI APIs"""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "openai"):
        """
        Initialize AI summarizer
        
        Args:
            api_key: API key for the AI service
            provider: AI provider ("openai", "anthropic", "local")
        """
        self.api_key = api_key
        self.provider = provider.lower()
    
    def generate_daily_summary(self, summary_data: Dict[str, Any], username: str, channel_name: str = None, channel_names: List[str] = None, language: str = "chinese", custom_prompt: Optional[str] = None) -> str:
        """
        Generate AI-powered daily summary
        
        Args:
            summary_data: Summary dictionary from StockMarketAnalyzer
            username: Username being analyzed
            channel_name: Channel name
            language: Language for summary ("chinese" or "english")
        
        Returns:
            AI-generated summary text
        """
        if not self.api_key:
            return "AI summarization not configured. Please set AI API key in config."
        
        # Prepare context for AI - ONLY use stock-related messages
        # The summary_data['messages'] already contains only stock-related messages
        stock_messages = summary_data.get("messages", [])
        
        if not stock_messages:
            channel_desc = f"在频道 {', '.join(channel_names)}" if channel_names and len(channel_names) > 1 else (f"在频道 {channel_name}" if channel_name else "")
            return f"未找到股票相关的消息。用户 {username} {channel_desc} 在过去24小时内没有发布任何股票市场相关的内容。"
        
        # Limit to 50 most recent stock-related messages for context (increased for multi-channel)
        messages_text = "\n\n".join([
            f"[{msg.get('timestamp', 'Unknown')}] {msg.get('content', '')}"
            for msg in stock_messages[:50]
        ])
        
        # Format orders information
        orders = summary_data.get('orders', [])
        orders_text = ""
        if orders:
            orders_text = "\n\n所有订单记录 (All Orders):\n"
            for i, order in enumerate(orders, 1):
                order_time = order.get('timestamp', 'Unknown')
                order_type = order.get('type', 'unknown').upper()
                ticker = order.get('ticker', 'N/A')
                quantity = order.get('quantity', 0)
                price = order.get('price', 0)
                
                if order_type == 'POSITION':
                    orders_text += f"{i}. [{order_time}] POSITION UPDATE: {ticker} @ ${price:.2f} (当前价格/成本)\n"
                elif quantity > 0:
                    orders_text += f"{i}. [{order_time}] {order_type}: {quantity} shares/contracts of {ticker} @ ${price:.2f}\n"
                else:
                    orders_text += f"{i}. [{order_time}] {order_type}: {ticker} @ ${price:.2f}\n"
        else:
            orders_text = "\n\n所有订单记录: 未找到订单信息\n"
        
        # Format P/L information
        pnl_list = summary_data.get('pnl', [])
        pnl_text = ""
        if pnl_list:
            pnl_text = "\n\n盈亏记录 (Profit/Loss):\n"
            total_pnl = 0
            for i, pnl in enumerate(pnl_list, 1):
                pnl_time = pnl.get('timestamp', 'Unknown')
                value = pnl.get('value', 0)
                pnl_type = pnl.get('type', 'unknown')
                is_percentage = pnl.get('is_percentage', False)
                note = pnl.get('note', '')
                
                if is_percentage:
                    sign = "+" if value >= 0 else ""
                    pnl_text += f"{i}. [{pnl_time}] {pnl_type.upper()}: {sign}{value:.1f}% {note}\n"
                elif note:
                    pnl_text += f"{i}. [{pnl_time}] {pnl_type.upper()}: {note}\n"
                else:
                    total_pnl += value
                    sign = "+" if value >= 0 else ""
                    pnl_text += f"{i}. [{pnl_time}] {pnl_type.upper()}: {sign}${value:.2f}\n"
            
            if total_pnl != 0:
                pnl_text += f"\n总盈亏 (Total P/L): {('+' if total_pnl >= 0 else '')}${total_pnl:.2f}\n"
        else:
            pnl_text = "\n\n盈亏记录: 未找到盈亏信息\n"
        
        # Check for messages with images (might contain P/L info we can't extract)
        messages_with_images = [msg for msg in stock_messages if msg.get('has_images', False)]
        if messages_with_images:
            pnl_text += f"\n注意: 有 {len(messages_with_images)} 条消息包含图片附件，可能包含额外的交易记录或盈亏信息（图片内容无法自动提取）\n"
        
        # Format channel name(s) for prompt
        if channel_names and len(channel_names) > 1:
            channel_desc = f"在以下频道中：{', '.join(channel_names)}"
            channel_name_for_prompt = ', '.join(channel_names)
        else:
            channel_desc = f"在频道 {channel_name}" if channel_name else ""
            channel_name_for_prompt = channel_name or "多个频道"
        
        # Use custom prompt if provided, otherwise use default
        if custom_prompt:
            # Replace placeholders in custom prompt
            prompt = custom_prompt.format(
                username=username,
                channel_name=channel_name_for_prompt,
                total_messages=summary_data.get('total_messages', 0),
                stock_related_count=summary_data.get('stock_related_messages', 0),
                tickers=', '.join(summary_data.get('tickers_mentioned', [])) or ('无' if language.lower() in ['chinese', 'zh'] else 'None'),
                date_range=f"{summary_data.get('date_range', {}).get('earliest', 'Unknown')} 至 {summary_data.get('date_range', {}).get('latest', 'Unknown')}" if language.lower() in ['chinese', 'zh'] else f"{summary_data.get('date_range', {}).get('earliest', 'Unknown')} to {summary_data.get('date_range', {}).get('latest', 'Unknown')}",
                messages_text=messages_text,
                orders_text=orders_text,
                pnl_text=pnl_text
            )
        elif language.lower() == "chinese" or language.lower() == "zh":
            # Default Chinese prompt (can be customized)
            default_prompt = """你是一位专业的金融分析师助手。请分析以下来自用户"{username}"{channel_desc}的股票市场消息，并创建一份全面的每日总结。

关键信息：
- 分析的消息总数：{total_messages}
- 股票相关消息：{stock_related_count}
- 提到的股票代码：{tickers}
- 日期范围：{date_range}

消息内容（仅包含股票相关消息，来自多个频道）：
{messages_text}

{orders_text}
{pnl_text}

重要提示：请务必在总结中分析上述订单记录和盈亏信息。如果没有订单记录，请明确说明"未检测到订单信息"。

请提供一份结构化的每日总结，包括：
1. **执行摘要**：用户交易活动和关键洞察的简要概述
2. **交易记录分析**：
   - 所有订单汇总（买入/卖出，包括数量、价格和时间）
   - 盈亏分析（如果有发布盈亏信息，包括总盈亏）
   - 持仓变化（注意原始持仓可能发生在24小时之前，需要从历史消息中推断）
3. **关键主题**：讨论的主要话题和策略
4. **股票分析**：对提到的股票/代码的详细分析，包括：
   - 看涨/看跌情绪
   - 提到的入场/出场点
   - 价格目标和止损位
   - 风险评估
5. **交易信号**：明确的买入/卖出信号
6. **市场展望**：整体市场情绪和预测
7. **行动项目**：关键要点和建议行动

请用清晰、专业的方式格式化总结，适合交易者和投资者阅读。特别注意分析用户的完整交易记录和盈亏情况。所有内容请使用中文。"""
            
            prompt = default_prompt.format(
                username=username,
                channel_desc=channel_desc,
                total_messages=summary_data.get('total_messages', 0),
                stock_related_count=summary_data.get('stock_related_messages', 0),
                tickers=', '.join(summary_data.get('tickers_mentioned', [])) or '无',
                date_range=f"{summary_data.get('date_range', {}).get('earliest', 'Unknown')} 至 {summary_data.get('date_range', {}).get('latest', 'Unknown')}",
                messages_text=messages_text,
                orders_text=orders_text,
                pnl_text=pnl_text
            )
        else:
            # Default English prompt (can be customized)
            default_prompt = """You are a financial analyst assistant. Analyze the following stock market messages from user "{username}"{channel_desc} and create a comprehensive daily summary.

Key Information:
- Total messages analyzed: {total_messages}
- Stock-related messages: {stock_related_count}
- Tickers mentioned: {tickers}
- Date range: {date_range}

Messages (only stock-related messages included, from multiple channels):
{messages_text}

{orders_text}
{pnl_text}

IMPORTANT: Please make sure to analyze the order records and P/L information above in your summary. If no orders were found, please explicitly state "No orders detected".

Please provide a structured daily summary that includes:
1. **Executive Summary**: Brief overview of the user's trading activity and key insights
2. **Trading Record Analysis**:
   - Summary of all orders (buy/sell, including quantities, prices, and timestamps)
   - Profit/Loss analysis (if P/L information was posted, including total P/L)
   - Position changes (note that original positions may have been established before the 24-hour window, infer from historical messages)
3. **Key Themes**: Main topics and strategies discussed
4. **Stock Analysis**: Detailed analysis of mentioned stocks/tickers with:
   - Bullish/bearish sentiment
   - Entry/exit points mentioned
   - Price targets and stop losses
   - Risk assessments
5. **Trading Signals**: Clear buy/sell signals identified
6. **Market Outlook**: Overall market sentiment and predictions
7. **Action Items**: Key takeaways and recommended actions

Format the summary in a clear, professional manner suitable for traders and investors. Pay special attention to analyzing the user's complete trading record and P/L performance."""
            
            prompt = default_prompt.format(
                username=username,
                channel_desc=channel_desc,
                total_messages=summary_data.get('total_messages', 0),
                stock_related_count=summary_data.get('stock_related_messages', 0),
                tickers=', '.join(summary_data.get('tickers_mentioned', [])) or 'None',
                date_range=f"{summary_data.get('date_range', {}).get('earliest', 'Unknown')} to {summary_data.get('date_range', {}).get('latest', 'Unknown')}",
                messages_text=messages_text
            )

        if self.provider == "openai":
            return self._openai_summarize(prompt)
        elif self.provider == "anthropic":
            return self._anthropic_summarize(prompt)
        elif self.provider == "gemini":
            return self._gemini_summarize(prompt)
        else:
            return f"Unsupported AI provider: {self.provider}. Use 'openai', 'anthropic', or 'gemini'."
    
    def _openai_summarize(self, prompt: str) -> str:
        """Summarize using OpenAI API"""
        try:
            # Try to import openai
            try:
                import openai
            except ImportError:
                return "OpenAI library not installed. Install with: pip install openai"
            
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using cheaper model, can change to gpt-4 for better quality
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst assistant specializing in stock market analysis and trading insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=8000  # Increased to allow full summary output
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating AI summary: {str(e)}"
    
    def _anthropic_summarize(self, prompt: str) -> str:
        """Summarize using Anthropic Claude API"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model="claude-3-haiku-20240307",  # Using cheaper model
                max_tokens=8000,  # Increased to allow full summary output
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except ImportError:
            return "Anthropic library not installed. Install with: pip install anthropic"
        except Exception as e:
            return f"Error generating AI summary: {str(e)}"
    
    def _gemini_summarize(self, prompt: str) -> str:
        """Summarize using Google Gemini API"""
        try:
            # Try new google.genai package first, then fallback to old package
            try:
                import google.genai as genai
                use_new_api = True
            except ImportError:
                try:
                    import google.generativeai as genai
                    use_new_api = False
                except ImportError:
                    return "Google Generative AI library not installed. Install with: pip install google-genai"
            
            if use_new_api:
                # New API (google.genai)
                client = genai.Client(api_key=self.api_key)
                
                # List available models first
                try:
                    models = client.models.list()
                    available_model_names = []
                    text_generation_models = []
                    
                    for model in models:
                        if hasattr(model, 'name'):
                            model_name = model.name
                            # Extract just the model name part (e.g., 'gemini-1.5-flash' from full path)
                            if '/' in model_name:
                                model_name = model_name.split('/')[-1]
                            
                            available_model_names.append(model_name)
                            
                            # Filter out embedding models and other non-text-generation models
                            if not any(skip in model_name.lower() for skip in ['embedding', 'imagen', 'veo', 'tts', 'audio', 'image-generation', 'computer-use', 'robotics', 'deep-research', 'aqa']):
                                # Prioritize Gemini 3 models first, then flash models, then others
                                if 'gemini-3' in model_name.lower():
                                    text_generation_models.insert(0, model_name)  # Highest priority - Gemini 3
                                elif 'flash' in model_name.lower() or 'latest' in model_name.lower():
                                    # Insert after Gemini 3 but before others
                                    gemini3_count = sum(1 for m in text_generation_models if 'gemini-3' in m.lower())
                                    text_generation_models.insert(gemini3_count, model_name)
                                else:
                                    text_generation_models.append(model_name)
                    
                    print(f"Found {len(text_generation_models)} text generation models")
                    
                    # Try models in order of preference (Gemini 3 first if available, then flash models for free tier)
                    models_to_try = [
                        'gemini-3-pro',
                        'gemini-3-flash',
                        'gemini-3-pro-preview',
                        'gemini-3-flash-preview',
                        'gemini-2.5-flash',
                        'gemini-flash-latest', 
                        'gemini-2.0-flash',
                        'gemini-2.5-flash-lite',
                        'gemini-flash-lite-latest',
                        'gemini-2.0-flash-lite',
                        'gemini-2.5-pro',
                        'gemini-pro-latest'
                    ]
                    
                    # First, try preferred models that are available
                    for preferred_model in models_to_try:
                        matching_models = [m for m in text_generation_models if preferred_model in m.lower()]
                        if matching_models:
                            model_to_use = matching_models[0]
                            print(f"Trying model: {model_to_use}")
                            try:
                                response = client.models.generate_content(
                                    model=model_to_use,
                                    contents=prompt,
                                    config=genai.types.GenerateContentConfig(
                                        temperature=0.7,
                                        max_output_tokens=8000,  # Increased to allow full summary output
                                    )
                                )
                                # Extract text from response
                                if hasattr(response, 'text'):
                                    return response.text
                                elif hasattr(response, 'candidates') and response.candidates:
                                    return response.candidates[0].content.parts[0].text
                                else:
                                    return str(response)
                            except Exception as e:
                                error_msg = str(e)
                                # Skip rate limit errors but try other models
                                if '429' in error_msg or 'quota' in error_msg.lower():
                                    print(f"Rate limit/quota exceeded for {model_to_use}, trying next model...")
                                    time.sleep(2)  # Brief delay
                                    continue
                                else:
                                    print(f"Error with model {model_to_use}: {error_msg[:100]}")
                                    continue
                    
                    # If no preferred model worked, try any text generation model
                    if text_generation_models:
                        for model_to_use in text_generation_models[:5]:  # Try first 5
                            print(f"Trying fallback model: {model_to_use}")
                            try:
                                response = client.models.generate_content(
                                    model=model_to_use,
                                    contents=prompt,
                                    config=genai.types.GenerateContentConfig(
                                        temperature=0.7,
                                        max_output_tokens=8000,  # Increased to allow full summary output
                                    )
                                )
                                if hasattr(response, 'text'):
                                    return response.text
                                elif hasattr(response, 'candidates') and response.candidates:
                                    return response.candidates[0].content.parts[0].text
                                else:
                                    return str(response)
                            except Exception as e:
                                error_msg = str(e)
                                if '429' in error_msg or 'quota' in error_msg.lower():
                                    print(f"Rate limit for {model_to_use}, waiting...")
                                    time.sleep(5)
                                    continue
                                continue
                    
                    return "No suitable text generation models found or all exceeded quota"
                        
                except Exception as e:
                    return f"Error listing/using models: {str(e)}"
            else:
                # Old API (google.generativeai) - deprecated but still works
                genai.configure(api_key=self.api_key)
                
                # List available models first
                try:
                    models = genai.list_models()
                    available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                    print(f"Available Gemini models: {available_models}")
                    
                    # Try models in order of preference (Gemini 3 first if available)
                    models_to_try = [
                        'gemini-3-pro',
                        'gemini-3-flash',
                        'gemini-3-pro-preview',
                        'gemini-3-flash-preview',
                        'gemini-1.5-flash', 
                        'gemini-1.5-pro', 
                        'gemini-1.0-pro', 
                        'gemini-pro'
                    ]
                    for model_name in models_to_try:
                        # Check if model is in available models
                        if any(model_name in m for m in available_models):
                            try:
                                model = genai.GenerativeModel(model_name)
                                response = model.generate_content(
                                    prompt,
                                    generation_config={
                                        "temperature": 0.7,
                                        "max_output_tokens": 8000,  # Increased to allow full summary output
                                    }
                                )
                                return response.text
                            except Exception as e:
                                continue
                    
                    # If none worked, try the first available model
                    if available_models:
                        model_name = available_models[0].split('/')[-1]
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(
                            prompt,
                            generation_config={
                                "temperature": 0.7,
                                "max_output_tokens": 2000,
                            }
                        )
                        return response.text
                    else:
                        return "No available Gemini models found"
                        
                except Exception as e:
                    return f"Error listing/using Gemini models: {str(e)}"
            
        except Exception as e:
            return f"Error generating AI summary with Gemini: {str(e)}"


def load_config(config_path: str, fallback_config: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Primary config file path
        fallback_config: Optional fallback config file (e.g., discord_config.yaml for token)
    
    Returns:
        Merged configuration dictionary
    """
    config = {}
    
    # Load fallback config first (for Discord token if not in main config)
    if fallback_config and os.path.exists(fallback_config):
        try:
            with open(fallback_config, 'r', encoding='utf-8') as f:
                fallback = yaml.safe_load(f)
                if fallback:
                    config.update(fallback)
        except Exception as e:
            print(f"Warning: Could not load fallback config {fallback_config}: {e}")
    
    # Load primary config (overrides fallback)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                primary = yaml.safe_load(f)
                if primary:
                    # Merge configs (primary overrides fallback)
                    def merge_dict(base: dict, override: dict):
                        for key, value in override.items():
                            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                                merge_dict(base[key], value)
                            else:
                                base[key] = value
                    
                    merge_dict(config, primary)
        except Exception as e:
            print(f"Error loading config {config_path}: {e}")
    elif not config:
        print(f"Warning: Config file {config_path} not found")
    
    return config


def main():
    parser = argparse.ArgumentParser(description="Summarize stock market messages from a Discord user")
    parser.add_argument("--config", "-c", type=str, default="config/summary_config.yaml",
                      help="Configuration file path (default: config/summary_config.yaml)")
    parser.add_argument("--discord-config", type=str, default="config/discord_config.yaml",
                      help="Fallback Discord config file for token (default: config/discord_config.yaml)")
    parser.add_argument("--channel", "-ch", type=str, action="append",
                      help="Channel ID to fetch messages from (can specify multiple times, or use --all-users)")
    parser.add_argument("--user", "-u", type=str, action="append",
                      help="Username to filter messages by (can specify multiple times, or use --all-users)")
    parser.add_argument("--all-users", action="store_true",
                      help="Generate summaries for all users in user_filters config (last 24 hours)")
    parser.add_argument("--max", "-m", type=int, default=None,
                      help="Maximum messages to fetch per user (default: from config or 500)")
    parser.add_argument("--output", "-o", type=str,
                      help="Output file path (default: print to console)")
    parser.add_argument("--ai", action="store_true",
                      help="Generate AI-powered summary")
    parser.add_argument("--ai-provider", type=str, default=None,
                      choices=["openai", "anthropic", "gemini"],
                      help="AI provider to use (default: from config or 'openai')")
    parser.add_argument("--ai-key", type=str,
                      help="AI API key (overrides config file)")
    parser.add_argument("--all-time", action="store_true",
                      help="Fetch all messages (default: last 24 hours only)")
    parser.add_argument("--language", "-l", type=str, default="chinese",
                      choices=["chinese", "english", "zh", "en"],
                      help="Language for summary (default: chinese)")
    parser.add_argument("--send-to-discord", action="store_true",
                      help="Send summary to Discord destination channel")
    parser.add_argument("--discord-channel", type=str,
                      help="Discord channel ID to send summary to (overrides config)")
    
    args = parser.parse_args()
    
    # Load configuration (with fallback to discord_config.yaml for token)
    config = load_config(args.config, fallback_config=args.discord_config)
    
    # Load primary config separately to get user_filters (don't merge with fallback)
    primary_config = {}
    if os.path.exists(args.config):
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                primary_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load primary config {args.config}: {e}")
    
    token = config.get("discord", {}).get("token")
    
    if not token:
        print("Error: Discord token not found in configuration file")
        print("Please set discord.token in your config file")
        sys.exit(1)
    
    # Initialize fetcher and analyzer
    fetcher = DiscordMessageFetcher(token)
    analyzer = StockMarketAnalyzer()
    
    # Determine which users and channels to process
    users_to_process = []
    channels_to_process = []
    
    if args.all_users:
        # Get all users from user_filters config - ONLY from primary config file (summary_config.yaml)
        # Don't use fallback config's user_filters to avoid old format conflicts
        # New format: user -> [channels]
        user_filters = primary_config.get("discord", {}).get("user_filters", {})
        
        # Check if it's old format (channel -> users) or new format (user -> channels)
        if user_filters:
            # Check first item to determine format
            first_key = list(user_filters.keys())[0]
            first_value = user_filters[first_key]
            
            # If first value is a list and looks like usernames (not numeric), it's old format
            # If first value is a list and looks like channel IDs (numeric strings), it's new format
            # If first key looks like a username (not numeric), it's new format
            is_old_format = first_key.isdigit() or (isinstance(first_value, list) and 
                                                    len(first_value) > 0 and 
                                                    not str(first_value[0]).isdigit())
            
            if is_old_format:
                # Old format: channel_id -> [users]
                print("Converting old format (channel->users) to new format (user->channels)...")
                converted = {}
                for channel_id, users in user_filters.items():
                    for user in users:
                        if user not in converted:
                            converted[user] = []
                        converted[user].append(channel_id)
                user_filters = converted
            
            # New format: user -> [channels]
            # Group by user to combine all channels for each user
            users_to_process_dict = {}
            for username, channels in user_filters.items():
                users_to_process_dict[username] = channels
            
            # Convert to list format: (username, [channel_ids])
            users_to_process = [(username, channels) for username, channels in users_to_process_dict.items()]
        
        if not users_to_process:
            print("Error: No user_filters found in config. Please configure user_filters in summary_config.yaml")
            print("Format: user_filters:")
            print('  "username1": ["channel_id1", "channel_id2"]')
            sys.exit(1)
    elif args.user and args.channel:
        # Use provided users and channels
        channels = args.channel if isinstance(args.channel, list) else [args.channel]
        users = args.user if isinstance(args.user, list) else [args.user]
        
        # If multiple channels but one user, apply user to all channels
        # If multiple users but one channel, apply all users to that channel
        # If both multiple, pair them up
        if len(channels) == 1 and len(users) > 1:
            # One channel, multiple users
            for user in users:
                users_to_process.append((channels[0], user))
        elif len(users) == 1 and len(channels) > 1:
            # Multiple channels, one user
            for channel_id in channels:
                users_to_process.append((channel_id, users[0]))
        elif len(channels) == len(users):
            # Same number, pair them up
            for channel_id, user in zip(channels, users):
                users_to_process.append((channel_id, user))
        else:
            # Default: apply all users to all channels
            for channel_id in channels:
                for user in users:
                    users_to_process.append((channel_id, user))
    elif not args.user or not args.channel:
        print("Error: Must specify --user and --channel, or use --all-users")
        print("\nExamples:")
        print("  # Process all users from config:")
        print("  python summarize_user_messages.py --all-users --ai --send-to-discord")
        print("\n  # Process specific users:")
        print("  python summarize_user_messages.py --channel CHANNEL1 --user user1 --user user2 --ai")
        print("\n  # Process multiple channels:")
        print("  python summarize_user_messages.py --channel CH1 --channel CH2 --user user1 --ai")
        sys.exit(1)
    
    if not users_to_process:
        print("No users to process")
        sys.exit(0)
    
    # Check if we're processing users with multiple channels (new format)
    is_multi_channel_format = users_to_process and isinstance(users_to_process[0], tuple) and isinstance(users_to_process[0][1], list)
    
    if is_multi_channel_format:
        total_channels = sum(len(channels) for _, channels in users_to_process)
        print(f"\n{'='*80}")
        print(f"Processing {len(users_to_process)} user(s) across {total_channels} channel(s)")
        print(f"Each user will have messages from all their channels combined into one summary")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}")
        print(f"Processing {len(users_to_process)} user-channel combination(s)")
        print(f"{'='*80}\n")
    
    # Process each user
    all_summaries = []
    
    # Fetch messages (default to last 24 hours unless --all-time is specified)
    last_24_hours = (not args.all_time and 
                    config.get("summary", {}).get("last_24_hours_only", True))
    max_msgs = args.max or config.get("summary", {}).get("max_messages", 500)
    
    for item in users_to_process:
        if is_multi_channel_format:
            # New format: (username, [channel_ids]) - combine all channels for one user
            username, channel_ids = item
            print(f"\n{'='*80}")
            print(f"Processing: {username} across {len(channel_ids)} channel(s)")
            print(f"{'='*80}")
            
            # Fetch messages from all channels for this user
            all_messages = []
            channel_names = []
            
            for channel_id in channel_ids:
                print(f"  Fetching messages from channel {channel_id}...")
                channel_info = fetcher.get_channel_info(channel_id)
                channel_name = channel_info.get("name", channel_id) if channel_info else channel_id
                channel_names.append(channel_name)
                
                messages = fetcher.fetch_all_user_messages(
                    channel_id, 
                    username, 
                    max_messages=max_msgs,
                    last_24_hours=last_24_hours
                )
                
                if messages:
                    print(f"    Found {len(messages)} messages from {channel_name}")
                    all_messages.extend(messages)
                else:
                    print(f"    No messages found in {channel_name}")
            
            if not all_messages:
                print(f"No messages found from user '{username}' in any configured channels")
                continue
            
            # Analyze and summarize all messages together
            print(f"\nAnalyzing {len(all_messages)} total messages for stock market content...")
            summary = analyzer.summarize_messages(all_messages, fetcher=fetcher)
            
            # Format basic summary
            formatted_summary = analyzer.format_summary(summary, username, channel_names=channel_names)
            
            # Generate AI summary if requested
            ai_summary = None
            if args.ai or config.get("ai", {}).get("enabled", False):
                print(f"\nGenerating AI-powered summary for {username} (combined from {len(channel_ids)} channels)...")
                ai_key = (args.ai_key or 
                         config.get("ai", {}).get("api_key") or 
                         os.getenv("OPENAI_API_KEY") or 
                         os.getenv("ANTHROPIC_API_KEY") or
                         os.getenv("GEMINI_API_KEY") or
                         os.getenv("GOOGLE_API_KEY"))
                ai_provider = args.ai_provider or config.get("ai", {}).get("provider", "gemini")
                language = args.language or config.get("summary", {}).get("language", "chinese")
                
                if ai_key:
                    # Get custom prompt from config if available
                    custom_prompt = config.get("ai", {}).get("custom_prompt")
                    
                    ai_summarizer = AISummarizer(api_key=ai_key, provider=ai_provider)
                    ai_summary = ai_summarizer.generate_daily_summary(
                        summary, 
                        username, 
                        channel_names=channel_names, 
                        language=language,
                        custom_prompt=custom_prompt
                    )
        else:
            # Old format: (channel_id, username) - single channel per user
            channel_id, username = item
            print(f"\n{'='*80}")
            print(f"Processing: {username} in channel {channel_id}")
            print(f"{'='*80}")
            
            # Get channel info
            channel_info = fetcher.get_channel_info(channel_id)
            channel_name = channel_info.get("name", channel_id) if channel_info else channel_id
            
            messages = fetcher.fetch_all_user_messages(
                channel_id, 
                username, 
                max_messages=max_msgs,
                last_24_hours=last_24_hours
            )
            
            if not messages:
                print(f"No messages found from user '{username}' in channel {channel_name}")
                continue
            
            # Analyze and summarize
            print(f"\nAnalyzing {len(messages)} messages for stock market content...")
            summary = analyzer.summarize_messages(messages, fetcher=fetcher)
            
            # Format basic summary
            formatted_summary = analyzer.format_summary(summary, username, channel_name)
            
            # Generate AI summary if requested
            ai_summary = None
            if args.ai or config.get("ai", {}).get("enabled", False):
                print(f"\nGenerating AI-powered summary for {username}...")
                ai_key = (args.ai_key or 
                         config.get("ai", {}).get("api_key") or 
                         os.getenv("OPENAI_API_KEY") or 
                         os.getenv("ANTHROPIC_API_KEY") or
                         os.getenv("GEMINI_API_KEY") or
                         os.getenv("GOOGLE_API_KEY"))
                ai_provider = args.ai_provider or config.get("ai", {}).get("provider", "gemini")
                language = args.language or config.get("summary", {}).get("language", "chinese")
                
                if ai_key:
                    # Get custom prompt from config if available
                    custom_prompt = config.get("ai", {}).get("custom_prompt")
                    
                    ai_summarizer = AISummarizer(api_key=ai_key, provider=ai_provider)
                    ai_summary = ai_summarizer.generate_daily_summary(
                        summary, 
                        username, 
                        channel_name, 
                        language=language,
                        custom_prompt=custom_prompt
                    )
                if ai_summary and not ai_summary.startswith("Error") and not "not installed" in ai_summary:
                    print(f"✓ AI summary generated for {username}")
                else:
                    print(f"⚠ {ai_summary}")
            else:
                print("⚠ AI API key not found. Set it in config file or use --ai-key parameter")
        
        # Send to Discord if requested
        auto_send = (args.send_to_discord or 
                    config.get("summary", {}).get("auto_send_to_discord", False) or
                    config.get("discord", {}).get("auto_send_summary", False))
        
        if auto_send:
            destination_channel_id = (args.discord_channel or 
                                     config.get("discord", {}).get("destination_channel_id"))
            
            if destination_channel_id and ai_summary:
                # Add header with user and channel info
                if is_multi_channel_format and channel_names:
                    channel_list = ", ".join(channel_names)
                    summary_header = f"**📊 {username} 的每日总结**\n**频道:** {channel_list}\n\n"
                else:
                    summary_header = f"**📊 {username} 的每日总结**\n**频道:** {channel_name}\n\n"
                full_summary = summary_header + ai_summary
                
                # Check if should send as PDF
                send_as_pdf = config.get("summary", {}).get("send_as_pdf", False)
                
                print(f"\nSending summary to Discord channel {destination_channel_id} as {'PDF' if send_as_pdf else 'text'}...")
                if fetcher.send_message(destination_channel_id, full_summary, as_pdf=send_as_pdf):
                    print(f"✓ Summary sent to Discord successfully for {username}")
                else:
                    print(f"✗ Failed to send summary to Discord for {username}")
        
        # Store summary for file output
        if is_multi_channel_format and 'channel_names' in locals():
            all_summaries.append({
                "user": username,
                "channels": channel_names,
                "channel_ids": channel_ids,
                "summary": summary,
                "formatted_summary": formatted_summary,
                "ai_summary": ai_summary
            })
        else:
            all_summaries.append({
                "user": username,
                "channel": channel_name,
                "channel_id": channel_id,
                "summary": summary,
                "formatted_summary": formatted_summary,
                "ai_summary": ai_summary
            })
    
    # Save all summaries to file
    if args.output:
        final_output = f"{'='*80}\n"
        final_output += f"DAILY SUMMARIES - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_output += f"{'='*80}\n\n"
        
        for item in all_summaries:
            final_output += f"\n{'='*80}\n"
            if 'channels' in item:
                channel_info = f"Channels: {', '.join(item['channels'])}"
            else:
                channel_info = f"Channel: {item['channel']}"
            final_output += f"User: {item['user']} | {channel_info}\n"
            final_output += f"{'='*80}\n\n"
            final_output += item['formatted_summary']
            
            if item['ai_summary']:
                final_output += "\n\n" + "=" * 80 + "\n"
                final_output += "AI-GENERATED DAILY SUMMARY\n"
                final_output += "=" * 80 + "\n\n"
                final_output += item['ai_summary']
            final_output += "\n\n"
        
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(final_output)
        
        # Also save raw summaries as JSON
        json_path = args.output.replace('.txt', '.json') if args.output.endswith('.txt') else args.output + '.json'
        json_data = {
            "generated_at": datetime.now().isoformat(),
            "summaries": [
                {
                    "user": item['user'],
                    "channel": item.get('channel'),
                    "channels": item.get('channels'),
                    "channel_id": item.get('channel_id'),
                    "channel_ids": item.get('channel_ids'),
                    "summary": item['summary'],
                    "ai_summary": item['ai_summary']
                }
                for item in all_summaries
            ]
        }
        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(json_data, jf, indent=2, ensure_ascii=False)
        
        print(f"\n✓ All summaries saved to: {args.output}")
        print(f"✓ JSON data saved to: {json_path}")
    else:
        # Print summaries
        for item in all_summaries:
            print(f"\n{'='*80}")
            if 'channels' in item:
                channel_info = f"Channels: {', '.join(item['channels'])}"
            else:
                channel_info = f"Channel: {item['channel']}"
            print(f"User: {item['user']} | {channel_info}")
            print(f"{'='*80}\n")
            print(item['formatted_summary'])
            if item['ai_summary']:
                print("\n" + "=" * 80)
                print("AI-GENERATED DAILY SUMMARY")
                print("=" * 80 + "\n")
                print(item['ai_summary'])


if __name__ == "__main__":
    main()

