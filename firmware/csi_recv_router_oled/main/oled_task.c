/*
 * SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/* OLED status display task, fed by host-hub lines over UART0 RX:
 *   "M1"/"M0"  motion ACTIVE/CLEAR
 *   "F<fps>"   CSI frame rate, e.g. F76
 *   "R<dbm>"   RSSI dBm, e.g. R-56
 *   "B<bpm>"   breathing rate, e.g. B15

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "ssd1306.h"
#include "oled_task.h"

#if CONFIG_OLED_ENABLE

#define OLED_TASK_TICK_MS       100
#define OLED_BREATH_TIMEOUT_MS  10000
#define OLED_FLASH_MS           200     /* invert flash on motion transition */

static const char *TAG = "oled_task";

static bool s_panel_ok;                 /* ssd1306_init() succeeded */

/* --- hub state --------------------------------------------------------*/
static bool s_motion_active;
static int s_fps = -1;
static int s_dbm = 0;
static int s_bpm = -1;                  /* -1 = no fresh value */
static TickType_t s_breath_ts;

/* --- UART line assembly -----------------------------------------------*/
static char s_line[32];
static size_t s_len;
static bool s_overflow;

static bool str_all_digits(const char *s)
{
    if (!*s) {
        return false;
    }
    while (*s) {
        if (*s < '0' || *s > '9') {
            return false;
        }
        s++;
    }
    return true;
}

static void handle_line(const char *l)
{
    if (!strcmp(l, "M1")) {
        s_motion_active = true;
    } else if (!strcmp(l, "M0")) {
        s_motion_active = false;
    } else if (l[0] == 'F' && str_all_digits(l + 1)) {
        s_fps = atoi(l + 1);
    } else if (l[0] == 'R' && (str_all_digits(l + 1) ||
             (l[1] == '-' && str_all_digits(l + 2)))) {
        s_dbm = atoi(l + 1);
    } else if (l[0] == 'B' && str_all_digits(l + 1)) {
        s_bpm = atoi(l + 1);
        s_breath_ts = xTaskGetTickCount();
    } else {
        ESP_LOGD(TAG, "drop: %s", l);
    }
}

static void feed_char(char c)
{
    if (c == '\r') {
        return;
    }
    if (c == '\n') {
        if (!s_overflow) {
            s_line[s_len] = '\0';
            handle_line(s_line);
        }
        s_len = 0;
        s_overflow = false;
        return;
    }
    if (s_len >= sizeof(s_line) - 1) {
        s_overflow = true;              /* garbage: drop the whole line */
        return;
    }
    s_line[s_len++] = c;
}

/* --- rendering ---------------------------------------------------------*/
static void render(void)
{
    static bool s_prev_motion;
    static bool s_inverted;
    static TickType_t s_flash_until;
    static char s_shown_l2[24], s_shown_l3[24], s_shown_l4[24];

    TickType_t now = xTaskGetTickCount();

    /* motion transition -> brief full-display invert for visibility */
    if (s_motion_active != s_prev_motion) {
        s_prev_motion = s_motion_active;
        ssd1306_invert(true);
        s_inverted = true;
        s_flash_until = now + pdMS_TO_TICKS(OLED_FLASH_MS);
    } else if (s_inverted && (int32_t)(now - s_flash_until) >= 0) {
        ssd1306_invert(false);
        s_inverted = false;
    }

    bool breath_fresh = s_bpm >= 0 &&
            (now - s_breath_ts) <= pdMS_TO_TICKS(OLED_BREATH_TIMEOUT_MS);

    char l2[24], l3[24], l4[24];
    snprintf(l2, sizeof(l2), "MOTION: %s", s_motion_active ? "ACTIVE" : "CLEAR");
    if (breath_fresh) {
        snprintf(l3, sizeof(l3), "BREATH: %d/min", s_bpm);
    } else {
        snprintf(l3, sizeof(l3), "BREATH: --");
    }
    if (s_fps >= 0) {
        snprintf(l4, sizeof(l4), "%dfps %ddBm", s_fps, s_dbm);
    } else {
        snprintf(l4, sizeof(l4), "--fps %ddBm", s_dbm);
    }

    /* redraw only when something actually changed */
    if (!strcmp(s_shown_l2, l2) && !strcmp(s_shown_l3, l3) &&
            !strcmp(s_shown_l4, l4)) {
        return;
    }
    strcpy(s_shown_l2, l2);
    strcpy(s_shown_l3, l3);
    strcpy(s_shown_l4, l4);

    ssd1306_clear();
    ssd1306_draw_string(0, 0, "CSI SENTINEL");
    ssd1306_draw_string(0, 16, l2);
    ssd1306_draw_string(0, 24, l3);
    ssd1306_draw_string(0, 32, l4);
    ssd1306_display();
}

static void oled_task(void *arg)
{
    /* UART0 is the console; the host hub writes status lines into its RX.
     * Keep the console baud/pins and just take over RX with a driver. */
    uart_driver_install(UART_NUM_0, 512, 0, 0, NULL, 0);

    uint8_t chunk[64];
    for (;;) {
        int n;
        while ((n = uart_read_bytes(UART_NUM_0, chunk, sizeof(chunk),
                0)) > 0) {          /* timeout 0: non-blocking */
            for (int i = 0; i < n; i++) {
                feed_char((char)chunk[i]);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(OLED_TASK_TICK_MS));
        render();
    }
}

void oled_show_boot(void)
{
    if (ssd1306_init() != ESP_OK) {
        ESP_LOGW(TAG, "SSD1306 init failed");
        return;
    }
    s_panel_ok = true;
    ssd1306_draw_string(0, 16, "BOOT...");
    ssd1306_display();
}

void oled_show_no_wifi(void)
{
    if (!s_panel_ok) {
        return;
    }
    ssd1306_clear();
    ssd1306_draw_string(0, 0, "CSI SENTINEL");
    ssd1306_draw_string(0, 16, "NO WIFI");
    ssd1306_display();
}

void oled_task_start(void)
{
    if (!s_panel_ok) {
        return;                         /* panel absent: stay silent */
    }
    xTaskCreate(oled_task, "oled_task", 4096, NULL, 4, NULL);
}

#endif /* CONFIG_OLED_ENABLE */
