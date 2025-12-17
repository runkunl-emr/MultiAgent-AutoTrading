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

class DiscordMessageFetcher:
    """Fetch messages from Discord channels"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
    
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
    
    def send_message(self, channel_id: str, content: str) -> bool:
        """
        Send a message to a Discord channel
        
        Args:
            channel_id: Discord channel ID
            content: Message content
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/channels/{channel_id}/messages"
        
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
        """Check if message content is related to stock market"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.stock_keywords)
    
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
    
    def summarize_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        
        for msg in messages:
            content = msg.get("content", "")
            if not content:
                # Try to get content from embeds
                embeds = msg.get("embeds", [])
                for embed in embeds:
                    if "description" in embed:
                        content += " " + embed["description"]
                    if "title" in embed:
                        content += " " + embed["title"]
            
            if self.is_stock_related(content):
                stock_messages.append({
                    "content": content,
                    "timestamp": msg.get("timestamp", ""),
                    "id": msg.get("id", "")
                })
                
                # Extract tickers
                tickers = self.extract_tickers(content)
                all_tickers.update(tickers)
                
                # Parse timestamp
                try:
                    dt = datetime.fromisoformat(msg.get("timestamp", "").replace('Z', '+00:00'))
                    message_dates.append(dt)
                except:
                    pass
        
        # Generate summary
        summary = {
            "total_messages": len(messages),
            "stock_related_messages": len(stock_messages),
            "tickers_mentioned": sorted(list(all_tickers)),
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
                messages_text=messages_text
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

请提供一份结构化的每日总结，包括：
1. **执行摘要**：用户交易活动和关键洞察的简要概述
2. **关键主题**：讨论的主要话题和策略
3. **股票分析**：对提到的股票/代码的详细分析，包括：
   - 看涨/看跌情绪
   - 提到的入场/出场点
   - 价格目标和止损位
   - 风险评估
4. **交易信号**：明确的买入/卖出信号
5. **市场展望**：整体市场情绪和预测
6. **行动项目**：关键要点和建议行动

请用清晰、专业的方式格式化总结，适合交易者和投资者阅读。所有内容请使用中文。"""
            
            prompt = default_prompt.format(
                username=username,
                channel_desc=channel_desc,
                total_messages=summary_data.get('total_messages', 0),
                stock_related_count=summary_data.get('stock_related_messages', 0),
                tickers=', '.join(summary_data.get('tickers_mentioned', [])) or '无',
                date_range=f"{summary_data.get('date_range', {}).get('earliest', 'Unknown')} 至 {summary_data.get('date_range', {}).get('latest', 'Unknown')}",
                messages_text=messages_text
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

Please provide a structured daily summary that includes:
1. **Executive Summary**: Brief overview of the user's trading activity and key insights
2. **Key Themes**: Main topics and strategies discussed
3. **Stock Analysis**: Detailed analysis of mentioned stocks/tickers with:
   - Bullish/bearish sentiment
   - Entry/exit points mentioned
   - Price targets and stop losses
   - Risk assessments
4. **Trading Signals**: Clear buy/sell signals identified
5. **Market Outlook**: Overall market sentiment and predictions
6. **Action Items**: Key takeaways and recommended actions

Format the summary in a clear, professional manner suitable for traders and investors."""
            
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
                max_tokens=2000
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
                max_tokens=2000,
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
                                        max_output_tokens=2000,
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
                                        max_output_tokens=2000,
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
                                        "max_output_tokens": 2000,
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
            summary = analyzer.summarize_messages(all_messages)
            
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
            summary = analyzer.summarize_messages(messages)
            
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
                
                print(f"\nSending summary to Discord channel {destination_channel_id}...")
                if fetcher.send_message(destination_channel_id, full_summary):
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

