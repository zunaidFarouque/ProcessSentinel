# Notification Channels & Alert Routing

ProcessSentinel features a flexible multi-channel alert routing engine. You can configure multiple destination endpoints across **ntfy.sh**, **Telegram**, **Discord**, and **Slack**, directing different types of alerts to different recipients and shared team channels.

---

## 📡 Supported Providers

| Provider | Configuration Fields | Use Case |
| :--- | :--- | :--- |
| **ntfy.sh** | Topic URL (e.g. `https://ntfy.sh/my_alerts`), Optional Access Token | Instant push notifications to Android, iOS, and Web. |
| **Telegram Bot** | Bot API Token (from `@BotFather`), Chat ID (Group or User) | Direct group/channel messaging within Telegram. |
| **Discord Webhook** | Discord Webhook URL (`https://discord.com/api/webhooks/...`) | Team alerts in dedicated Discord server channels. |
| **Slack Webhook** | Slack Incoming Webhook URL (`https://hooks.slack.com/services/...`) | Incident notifications in Slack team workspaces. |

---

## 📡 Core Concepts

### 1. Topic Aliases
Instead of hardcoding raw URLs across your rules, ProcessSentinel introduces **Channels with Aliases**. A channel consists of:
* **Friendly Name**: (e.g. `"My Phone"`, `"Research Lab Channel"`, `"Emergency Server On-Call"`).
* **Provider Type**: ntfy.sh, Telegram, Discord, or Slack.
* **Credentials / Endpoint**: Dedicated connection details per provider.

### 2. The Default Channel
One channel is designated as the **Default Channel** (`[Default]`).
* When creating a monitor, you can leave its channel set to `[Inherit Default Channel]`.
* If you ever switch the default channel, all inheriting monitors automatically route to the new target without requiring individual edits.

### 3. Per-Monitor Channel Overrides
You can assign specific monitors to distinct channels:
* Send routine batch completion updates to your personal phone or Telegram.
* Send critical server, GPU, or storage failures to a shared lab team Discord or Slack channel.

---

## ⚡ Remote Action Listener

ProcessSentinel includes an optional **Remote Command Listener** that securely listens for push commands:
* **Actions Supported**: `run_action` (triggers a monitor's configured self-healing script), `reset` (flushes state/latches), and `check_now` (forces immediate inspection).
* **Security**: Enforces token authentication (`auth_token` / shared secret) to guarantee only authorized commands are executed.

---

## 🔔 Priority Levels & Tags Mapping

ProcessSentinel automatically sets ntfy priority headers and emoji tags based on the severity of the event:

| Severity Level | ntfy Priority | Mobile Behavior | ProcessSentinel Tags |
| :--- | :--- | :--- | :--- |
| **Info / Step-Down** | `3` (Default) | Standard notification, soft ring/vibrate | ℹ️ `information_source` |
| **Warning** | `4` (High) | Louder ringtone, prominent banner | ⚠️ `warning` |
| **Critical / Fatal** | `5` (Max / Urgent) | Continuous alarm sound; can override Do-Not-Disturb on Android | 🚨 `rotating_light`, `fire` |

> [!NOTE]
> On Android devices, priority `5` (Urgent) notifications can wake the screen and trigger sound even when phone volume is low if permission is granted in the ntfy app.

---

## 🛠️ Managing Channels in the Dashboard

### Adding a Channel
1. Open the **Notification Channels** tab.
2. Click **+ Add Channel** at the top right.
3. Enter an alias name and the full topic URL.
4. Click **Save Channel**.

### Testing Connectivity
* Every channel card features a **Test Alert** button.
* When clicked, ProcessSentinel dispatches a background asynchronous test request.
* The button temporarily displays `"Sending..."` while the HTTP POST executes. The main UI thread remains fluid and responsive.
* If successful, an informational pop-up confirms delivery, and your device will chime immediately.

### Setting as Default
* To make any channel the primary destination, click the **Set as Default** button on its card.
* The `[Default]` badge updates immediately, and all monitors set to `[Inherit Default Channel]` will begin routing to this endpoint.

---

## 🔒 Security Best Practices

1. **Keep Topic Names Private**: Anyone who knows your topic URL can receive your alerts or send fake messages to your topic. Combine words with random alphanumeric strings (e.g., `ps-compute-99824-z1`).
2. **Rate Limits on Public ntfy.sh**: The public `ntfy.sh` server is generous and free, but has rate limits (~250 messages per day per IP). ProcessSentinel monitors are stateful and designed specifically to avoid alert flooding.
3. **Private Subnets & Self-Hosting**: For confidential research environments or air-gapped networks, deploy ntfy via Docker on your local network. ProcessSentinel works seamlessly with local endpoints (e.g. `http://192.168.1.50:8080/my-topic`).

---

## ⏭️ Next Step

See practical monitoring configurations in action in **[Real-World Use Cases & Cookbooks](use-cases.md)**.
