# Mobile Push Notifications Setup (Android & iOS)

ProcessSentinel delivers alerts directly to your mobile phone or tablet using **[ntfy.sh](https://ntfy.sh)**, a high-performance, open-source HTTP-based pub-sub notification service.

### 🌟 Why ntfy?
* **Zero Registration**: No user accounts, passwords, API keys, or credit cards required.
* **Open Source & Privacy Friendly**: Messages are not tracked, logged, or monetized.
* **Instant Delivery**: Sub-second latency via HTTP/2 and WebSockets.
* **Multi-Platform**: Native mobile apps for Android and iOS, desktop web notifications, and self-hosted server support.

---

## 📱 1. Install the Mobile App

Install the official, free ntfy client on your device:

### Android
* **Google Play Store**: [Download from Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
* **F-Droid (Open Source)**: [Download on F-Droid](https://f-droid.org/en/packages/io.heckel.ntfy/)
* **Direct APK**: [GitHub Android Releases](https://github.com/binwiederhier/ntfy-android/releases)

### Apple iOS (iPhone & iPad)
* **Apple App Store**: [Download from App Store](https://apps.apple.com/app/ntfy/id1625396347)

### Web Browser / Desktop (No Phone Required)
* You can also receive notifications in Chrome, Firefox, or Edge on any computer by visiting [ntfy.sh](https://ntfy.sh) and clicking **Subscribe to topic**.

---

## 🔒 2. Choose a Secure Topic Name

On the public `ntfy.sh` server, any topic you subscribe to can be listened to if someone guesses the name. Therefore, **use a unique, unguessable topic name** for your workstation or laboratory.

> [!TIP]
> **Good Topic Names**:
> * `ps-lab4-sim-x89f2a`
> * `watchdog-john-render-9142`
> * `sentinel-compute-rig-z5`
>
> **Avoid Obvious Names**:
> * `alerts`, `test`, `sim`, `monitor`, `server`

---

## 📲 3. Subscribe on Your Phone

1. Open the **ntfy** app on your phone.
2. Tap the **`+`** (or **Subscribe**) button in the top/bottom corner.
3. In the **Topic name** field, type your secret topic name (for example, `ps-lab4-sim-x89f2a`).
4. If using the default public service, ensure the server is set to `ntfy.sh`.
5. Tap **Subscribe**.

Your phone is now actively listening for incoming alerts on this topic!

---

## 🖥️ 4. Configure ProcessSentinel

Now connect ProcessSentinel to your new topic:

1. Open the ProcessSentinel dashboard.
2. Click the **Notification Channels** tab.
3. If using the default channel, click **Edit** (or click **+ Add New Channel**).
4. Fill in the channel details:
   * **Channel Name**: A friendly label (e.g., `My Phone`, `Lab Rig Alert`).
   * **ntfy.sh Endpoint URL**: Enter the full URL:
     ```text
     https://ntfy.sh/ps-lab4-sim-x89f2a
     ```
5. Click **Save Channel**.
6. Click the **Test Alert** button next to your channel.
   * ProcessSentinel will show `Sending...` while dispatching the test packet.
   * Within a fraction of a second, your phone will ring/vibrate with a test notification:
     ```text
     [ProcessSentinel] Test Notification: Channel 'My Phone' is working properly! 🚀
     ```

---

## 🏢 5. Using a Self-Hosted ntfy Server (Optional)

If your lab or enterprise prohibits using public internet services, you can run your own ntfy server behind your firewall (via Docker or Linux package). 

ProcessSentinel is fully compatible with private ntfy instances:
1. When configuring a channel in ProcessSentinel, simply specify your self-hosted URL:
   ```text
   https://ntfy.internal.mylab.edu/simulation-alerts
   ```
2. In the mobile app, when adding a subscription, change the server address to match your self-hosted domain.

---

## ⚙️ 6. Ensuring Reliable Background Delivery

To ensure your device never sleeps through an overnight alert:

* **Android**: In Android Settings → Apps → ntfy → Battery, select **Unrestricted**. Also enable **Autostart** if your device uses custom Android skins (Xiaomi, OnePlus, Samsung).
* **iOS**: Ensure **Background App Refresh** and **Notifications** are toggled on in iOS Settings → ntfy.

---

## ⏭️ Next Step

Now that mobile notifications are verified, learn how to configure your monitoring rules in the **[Complete Monitors Guide & Reference](monitors-guide.md)**.
