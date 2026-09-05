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
#pragma once

#include "sdkconfig.h"

#if CONFIG_OLED_ENABLE

/* Show "BOOT..." splash (initialises the panel). Call before connecting. */
void oled_show_boot(void);

/* Show "NO WIFI" screen (connect failed). */
void oled_show_no_wifi(void);

/* Start the 100 ms status-display task. Call after example_connect() succeeds. */
void oled_task_start(void);

#else

static inline void oled_show_boot(void) {}
static inline void oled_show_no_wifi(void) {}
static inline void oled_task_start(void) {}

#endif /* CONFIG_OLED_ENABLE */
