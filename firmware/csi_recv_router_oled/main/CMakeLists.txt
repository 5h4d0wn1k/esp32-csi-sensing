idf_component_register(SRC_DIRS "."
                       INCLUDE_DIRS "."
                       REQUIRES nvs_flash esp_wifi esp_event esp_netif lwip
                                protocol_examples_common
                                esp_driver_i2c esp_driver_uart)
