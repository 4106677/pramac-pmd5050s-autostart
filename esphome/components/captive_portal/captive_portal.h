// Local copy of ESPHome 2025.2 captive_portal with our own page (web/wifi.html -> captive_index.h).
// Changes: the page is also at /wifi and /config.json, /wifisave work while connected to the home network
// ("Change Wi-Fi network" on the control page); SSIDs are JSON-escaped.
#pragma once
#include "esphome/core/defines.h"
#ifdef USE_CAPTIVE_PORTAL
#include <memory>
#ifdef USE_ARDUINO
#include <DNSServer.h>
#endif
#include "esphome/core/component.h"
#include "esphome/core/helpers.h"
#include "esphome/core/preferences.h"
#include "esphome/components/web_server_base/web_server_base.h"

namespace esphome {

namespace captive_portal {

class CaptivePortal : public AsyncWebHandler, public Component {
 public:
  CaptivePortal(web_server_base::WebServerBase *base);
  void setup() override;
  void dump_config() override;
#ifdef USE_ARDUINO
  void loop() override {
    if (this->dns_server_ != nullptr)
      this->dns_server_->processNextRequest();
  }
#endif
  float get_setup_priority() const override;
  void start();
  bool is_active() const { return this->active_; }
  void end() {
    this->active_ = false;
    this->base_->deinit();
#ifdef USE_ARDUINO
    this->dns_server_->stop();
    this->dns_server_ = nullptr;
#endif
  }

  bool canHandle(AsyncWebServerRequest *request) override {

    if (request->method() != HTTP_GET)
      return false;
    const auto &url = request->url();
    if (url == "/wifi" || url == "/config.json" || url == "/wifisave")
      return true;
    return this->active_ && url == "/";
  }

  void handle_config(AsyncWebServerRequest *request);

  void handle_wifisave(AsyncWebServerRequest *request);

  void handleRequest(AsyncWebServerRequest *req) override;

 protected:
  web_server_base::WebServerBase *base_;
  bool initialized_{false};
  bool ota_added_{false};
  bool active_{false};
#ifdef USE_ARDUINO
  std::unique_ptr<DNSServer> dns_server_{nullptr};
#endif
};

extern CaptivePortal *global_captive_portal;  // NOLINT(cppcoreguidelines-avoid-non-const-global-variables)

}  // namespace captive_portal
}  // namespace esphome
#endif
