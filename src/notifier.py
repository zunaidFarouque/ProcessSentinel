import requests

class Notifier:
    def __init__(self, topic_url=""):
        """
        Initializes the Notifier with a target ntfy.sh URL.
        Example: https://ntfy.sh/mzf_FAU_GRA_Monitoring
        """
        self.topic_url = topic_url

    def set_topic(self, url):
        """Allows updating the topic dynamically from the GUI."""
        self.topic_url = url

    def send(self, message, title="ProcessSentinel Alert", tags=""):
        """
        Constructs and sends the HTTP POST request to the ntfy server.
        """
        if not self.topic_url:
            return False

        headers = {"Title": title}
        if tags:
            headers["Tags"] = tags
            
        try:
            # The 5-second timeout ensures the monitoring thread never freezes on a bad connection
            response = requests.post(
                self.topic_url, 
                data=message.encode('utf-8'), 
                headers=headers, 
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            # Fails silently so the background daemon loop continues running without crashing
            print(f"Network error: Failed to send notification. Details: {e}")
            return False

# --- Quick Test ---
if __name__ == "__main__":
    test_notifier = Notifier("https://ntfy.sh/mzf_FAU_GRA_Monitoring")
    success = test_notifier.send("Notifier module is working correctly.", "Module Test", "white_check_mark")
    print(f"Notification sent successfully: {success}")