// PUKANKOV ticket kiosk: ESP32 + ILI9341/FT6206 + MFRC522.
// The card is read locally. No UID or card data is sent to the API.
// Provision once in Serial Monitor: KEY your_device_key
// When the tunnel changes: URL https://your-new-tunnel.trycloudflare.com
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <Wire.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <Adafruit_FT6206.h>
#include <U8g2_for_Adafruit_GFX.h>
#include <MFRC522.h>
#include <time.h>
#include <mbedtls/x509_crt.h>
#include <vector>

static const char WIFI_SSID[] = "Wokwi-GUEST";
static const char WIFI_PASSWORD[] = "";
static const char DEFAULT_API_URL[] = "https://foil-reoccur-tablet.ngrok-free.dev";

static const char PINNED_API_HOST[] = "foil-reoccur-tablet.ngrok-free.dev";
static const char PINNED_CERT_SHA256[] = "602e1f88fa62519ede85a4da6b9ef6204788f7c6d31eeeebe23cb93587477e94";

// Trusted public CA certificates are inserted by prepare_kiosk.py.
static const char ROOT_CA[] PROGMEM = R"PEM(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAwTzELMAkG
A1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2VhcmNoIEdyb3VwMRUw
EwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4WhcNMzUwNjA0MTEwNDM4WjBP
MQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJuZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3Jv
dXAxFTATBgNVBAMTDElTUkcgUm9vdCBYMTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoC
ggIBAK3oJHP0FDfzm54rVygch77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj
/RQSa78f0uoxmyF+0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7i
S4+3mX6UA5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyHB5T0Y3Hs
LuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UCB5iPNgiV5+I3lg02
dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUvKBds0pjBqAlkd25HN7rOrFle
aJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWnOlFuhjuefXKnEgV4We0+UXgVCwOPjdAv
BbI+e0ocS3MFEvzG6uBQE3xDk3SzynTnjh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymC
zLq9gwQbooMDQaHWBfEbwrbwqHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC
1CLQJ13hef4Y53CIrU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIB
BjAPBgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZLubhzEFnT
IZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ3BebYhtF8GaV0nxv
wuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KKNFtY2PwByVS5uCbMiogziUwt
hDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5ORAzI4JMPJ+GslWYHb4phowim57iaztX
OoJwTdwJx4nLCgdNbOhdjsnvzqvHu7UrTkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIu
vtd7u+Nxe5AW0wdeRlN8NwdCjNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1N
bdWhscdCb+ZAJzVcoyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4k
qKOJ2qxq4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57demyPxgcY
xn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIICGzCCAaGgAwIBAgIQQdKd0XLq7qeAwSxs6S+HUjAKBggqhkjOPQQDAzBPMQswCQYDVQQG
EwJVUzEpMCcGA1UEChMgSW50ZXJuZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNV
BAMTDElTUkcgUm9vdCBYMjAeFw0yMDA5MDQwMDAwMDBaFw00MDA5MTcxNjAwMDBaME8xCzAJ
BgNVBAYTAlVTMSkwJwYDVQQKEyBJbnRlcm5ldCBTZWN1cml0eSBSZXNlYXJjaCBHcm91cDEV
MBMGA1UEAxMMSVNSRyBSb290IFgyMHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEzZvVn4CDCuwJ
SvMWSj5cz3es3mcFDR0HttwW+1qLFNvicWDEukWVEYmO6gbf9yoWHKS5xcUy4APgHoIYOIvX
RdgKam7mAHf7AlF9ItgKbppbd9/w+kHsOdx1ymgHDB/qo0IwQDAOBgNVHQ8BAf8EBAMCAQYw
DwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUfEKWrt5LSDv6kviejM9ti6lyN5UwCgYIKoZI
zj0EAwMDaAAwZQIwe3lORlCEwkSHRhtFcP9Ymd70/aTSVaYgLXTWNLxBo1BfASdWtL4ndQav
Ei51mI38AjEAi/V3bNTIZargCyzuFJ0nN6T5U6VR5CmD1/iQMVtCnwr1/q4AaOeMSQ+2b1tb
FfLn
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIFVzCCAz+gAwIBAgINAgPlk28xsBNJiGuiFzANBgkqhkiG9w0BAQwFADBHMQswCQYDVQQG
EwJVUzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RT
IFJvb3QgUjEwHhcNMTYwNjIyMDAwMDAwWhcNMzYwNjIyMDAwMDAwWjBHMQswCQYDVQQGEwJV
UzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RTIFJv
b3QgUjEwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQC2EQKLHuOhd5s73L+UPreV
p0A8of2C+X0yBoJx9vaMf/vo27xqLpeXo4xL+Sv2sfnOhB2x+cWX3u+58qPpvBKJXqeqUqv4
IyfLpLGcY9vXmX7wCl7raKb0xlpHDU0QM+NOsROjyBhsS+z8CZDfnWQpJSMHobTSPS5g4M/S
CYe7zUjwTcLCeoiKu7rPWRnWr4+wB7CeMfGCwcDfLqZtbBkOtdh+JhpFAz2weaSUKK0Pfybl
qAj+lug8aJRT7oM6iCsVlgmy4HqMLnXWnOunVmSPlk9orj2XwoSPwLxAwAtcvfaHszVsrBhQ
f4TgTM2S0yDpM7xSma8ytSmzJSq0SPly4cpk9+aCEI3oncKKiPo4Zor8Y/kB+Xj9e1x3+naH
+uzfsQ55lVe0vSbv1gHR6xYKu44LtcXFilWr06zqkUspzBmkMiVOKvFlRNACzqrOSbTqn3yD
sEB750Orp2yjj32JgfpMpf/VjsPOS+C12LOORc92wO1AK/1TD7Cn1TsNsYqiA94xrcx36m97
PtbfkSIS5r762DL8EGMUUXLeXdYWk70paDPvOmbsB4om3xPXV2V4J95eSRQAogB/mqghtqmx
lbCluQ0WEdrHbEg8QOB+DVrNVjzRlwW5y0vtOUucxD/SVRNuJLDWcfr0wbrM7Rv1/oFB2ACY
PTrIrnqYNxgFlQIDAQABo0IwQDAOBgNVHQ8BAf8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB/zAd
BgNVHQ4EFgQU5K8rJnEaK0gnhS9SZizv8IkTcT4wDQYJKoZIhvcNAQEMBQADggIBAJ+qQibb
C5u+/x6Wki4+omVKapi6Ist9wTrYggoGxval3sBOh2Z5ofmmWJyq+bXmYOfg6LEeQkEzCzc9
zolwFcq1JKjPa7XSQCGYzyI0zzvFIoTgxQ6KfF2I5DUkzps+GlQebtuyh6f88/qBVRRiClmp
IgUxPoLW7ttXNLwzldMXG+gnoot7TiYaelpkttGsN/H9oPM47HLwEXWdyzRSjeZ2axfG34ar
J45JK3VmgRAhpuo+9K4l/3wV3s6MJT/KYnAK9y8JZgfIPxz88NtFMN9iiMG1D53Dn0reWVlH
xYciNuaCp+0KueIHoI17eko8cdLiA6EfMgfdG+RCzgwARWGAtQsgWSl4vflVy2PFPEz0tv/b
al8xa5meLMFrUKTX5hgUvYU/Z6tGn6D/Qqc6f1zLXbBwHSs09dR2CQzreExZBfMzQsNhFRAb
d03OIozUhfJFfbdT6u9AWpQKXCBfTkBdYiJ23//OYb2MI3jSNwLgjt7RETeJ9r/tSQdirpLs
QBqvFAnZ0E6yove+7u7Y/9waLd64NnHi/Hm3lCXRSHNboTXns5lndcEZOitHTtNCjv0xyBZm
2tIMPNuzjsmhDYAPexZ3FL//2wmUspO8IFgV6dtxQ/PeEMMA3KgqlbbC1j+Qa3bbbP6MvPJw
NQzcmRk13NfIRmPVNnGuV/u3gm3c
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIFVzCCAz+gAwIBAgINAgPlrsWNBCUaqxElqjANBgkqhkiG9w0BAQwFADBHMQswCQYDVQQG
EwJVUzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RT
IFJvb3QgUjIwHhcNMTYwNjIyMDAwMDAwWhcNMzYwNjIyMDAwMDAwWjBHMQswCQYDVQQGEwJV
UzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RTIFJv
b3QgUjIwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQDO3v2m++zsFDQ8BwZabFn3
GTXd98GdVarTzTukk3LvCvptnfbwhYBboUhSnznFt+4orO/LdmgUud+tAWyZH8QiHZ/+cnfg
LFuv5AS/T3KgGjSY6Dlo7JUle3ah5mm5hRm9iYz+re026nO8/4Piy33B0s5Ks40FnotJk9/B
W9BuXvAuMC6C/Pq8tBcKSOWIm8Wba96wyrQD8Nr0kLhlZPdcTK3ofmZemde4wj7I0BOdre7k
RXuJVfeKH2JShBKzwkCX44ofR5GmdFrS+LFjKBC4swm4VndAoiaYecb+3yXuPuWgf9RhD1FL
PD+M2uFwdNjCaKH5wQzpoeJ/u1U8dgbuak7MkogwTZq9TwtImoS1mKPV+3PBV2HdKFZ1E66H
jucMUQkQdYhMvI35ezzUIkgfKtzra7tEscszcTJGr61K8YzodDqs5xoic4DSMPclQsciOzsS
rZYuxsN2B6ogtzVJV+mSSeh2FnIxZyuWfoqjx5RWIr9qS34BIbIjMt/kmkRtWVtd9QCgHJvG
eJeNkP+byKq0rxFROV7Z+2et1VsRnTKaG73VululycslaVNVJ1zgyjbLiGH7HrfQy+4W+9Om
TN6SpdTi3/UGVN4unUu0kzCqgc7dGtxRcw1PcOnlthYhGXmy5okLdWTK1au8CcEYof/UVKGF
PP0UJAOyh9OktwIDAQABo0IwQDAOBgNVHQ8BAf8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB/zAd
BgNVHQ4EFgQUu//KjiOfT5nK2+JopqUVJxce2Q4wDQYJKoZIhvcNAQEMBQADggIBAB/Kzt3H
vqGf2SdMC9wXmBFqiN495nFWcrKeGk6c1SuYJF2ba3uwM4IJvd8lRuqYnrYb/oM80mJhwQTt
zuDFycgTE1XnqGOtjHsB/ncw4c5omwX4Eu55MaBBRTUoCnGkJE+M3DyCB19m3H0Q/gxhswWV
7uGugQ+o+MePTagjAiZrHYNSVc61LwDKgEDg4XSsYPWHgJ2uNmSRXbBoGOqKYcl3qJfEycel
/FVL8/B/uWU9J2jQzGv6U53hkRrJXRqWbTKH7QMgyALOWr7Z6v2yTcQvG99fevX4i8buMTol
UVVnjWQye+mew4K6Ki3pHrTgSAai/GevHyICc/sgCq+dVEuhzf9gR7A/Xe8bVr2XIZYtCtFe
nTgCR2y59PYjJbigapordwj6xLEokCZYCDzifqrXPW+6MYgKBesntaFJ7qBFVHvmJ2WZICGo
o7z7GJa7Um8M7YNRTOlZ4iBgxcJlkoKM8xAfDoqXvneCbT+PHV28SSe9zE8P4c52hgQjxcCM
Elv924SgJPFI/2R80L5cFtHvma3AH/vLrrw4IgYmZNralw4/KBVEqE8AyvCazM90arQ+POuV
7LXTWtiBmelDGDfrs7vRWGJB82bSj6p4lVQgw1oudCvV0b4YacCs1aTPObpRhANl6WLAYv7Y
TVWW4tAR+kg0Eeye7QUd5MjWHYbL
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIICCTCCAY6gAwIBAgINAgPluILrIPglJ209ZjAKBggqhkjOPQQDAzBHMQswCQYDVQQGEwJV
UzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RTIFJv
b3QgUjMwHhcNMTYwNjIyMDAwMDAwWhcNMzYwNjIyMDAwMDAwWjBHMQswCQYDVQQGEwJVUzEi
MCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RTIFJvb3Qg
UjMwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAAQfTzOHMymKoYTey8chWEGJ6ladK0uFxh1MJ7x/
JlFyb+Kf1qPKzEUURout736GjOyxfi//qXGdGIRFBEFVbivqJn+7kAHjSxm65FSWRQmx1WyR
RK2EE46ajA2ADDL24CejQjBAMA4GA1UdDwEB/wQEAwIBhjAPBgNVHRMBAf8EBTADAQH/MB0G
A1UdDgQWBBTB8Sa6oC2uhYHP0/EqEr24Cmf9vDAKBggqhkjOPQQDAwNpADBmAjEA9uEglRR7
VKOQFhG/hMjqb2sXnh5GmCCbn9MN2azTL818+FsuVbu/3ZL3pAzcMeGiAjEA/JdmZuVDFhOD
3cffL74UOO0BzrEXGhF16b0DjyZ+hOXJYKaV11RZt+cRLInUue4X
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIICCTCCAY6gAwIBAgINAgPlwGjvYxqccpBQUjAKBggqhkjOPQQDAzBHMQswCQYDVQQGEwJV
UzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RTIFJv
b3QgUjQwHhcNMTYwNjIyMDAwMDAwWhcNMzYwNjIyMDAwMDAwWjBHMQswCQYDVQQGEwJVUzEi
MCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIGA1UEAxMLR1RTIFJvb3Qg
UjQwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAATzdHOnaItgrkO4NcWBMHtLSZ37wWHO5t5GvWvV
YRg1rkDdc/eJkTBa6zzuhXyiQHY7qca4R9gq55KRanPpsXI5nymfopjTX15YhmUPoYRlBtHc
i8nHc8iMai/lxKvRHYqjQjBAMA4GA1UdDwEB/wQEAwIBhjAPBgNVHRMBAf8EBTADAQH/MB0G
A1UdDgQWBBSATNbrdP9JNqPV2Py1PsVq8JQdjDAKBggqhkjOPQQDAwNpADBmAjEA6ED/g94D
9J+uHXqnLrmvT/aDHQ4thQEd0dlq7A/Cr8deVl5c1RxYIigL9zC2L7F8AjEA8GE8p/SgguMh
1YQdc4acLa/KNJvxn7kjNuK8YAOdgLOaVsjh4rsUecrNIdSUtUlD
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDejCCAmKgAwIBAgIQf+UwvzMTQ77dghYQST2KGzANBgkqhkiG9w0BAQsFADBX
MQswCQYDVQQGEwJCRTEZMBcGA1UEChMQR2xvYmFsU2lnbiBudi1zYTEQMA4GA1UE
CxMHUm9vdCBDQTEbMBkGA1UEAxMSR2xvYmFsU2lnbiBSb290IENBMB4XDTIzMTEx
NTAzNDMyMVoXDTI4MDEyODAwMDA0MlowRzELMAkGA1UEBhMCVVMxIjAgBgNVBAoT
GUdvb2dsZSBUcnVzdCBTZXJ2aWNlcyBMTEMxFDASBgNVBAMTC0dUUyBSb290IFI0
MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAE83Rzp2iLYK5DuDXFgTB7S0md+8Fhzube
Rr1r1WEYNa5A3XP3iZEwWus87oV8okB2O6nGuEfYKueSkWpz6bFyOZ8pn6KY019e
WIZlD6GEZQbR3IvJx3PIjGov5cSr0R2Ko4H/MIH8MA4GA1UdDwEB/wQEAwIBhjAd
BgNVHSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwDwYDVR0TAQH/BAUwAwEB/zAd
BgNVHQ4EFgQUgEzW63T/STaj1dj8tT7FavCUHYwwHwYDVR0jBBgwFoAUYHtmGkUN
l8qJUC99BM00qP/8/UswNgYIKwYBBQUHAQEEKjAoMCYGCCsGAQUFBzAChhpodHRw
Oi8vaS5wa2kuZ29vZy9nc3IxLmNydDAtBgNVHR8EJjAkMCKgIKAehhxodHRwOi8v
Yy5wa2kuZ29vZy9yL2dzcjEuY3JsMBMGA1UdIAQMMAowCAYGZ4EMAQIBMA0GCSqG
SIb3DQEBCwUAA4IBAQAYQrsPBtYDh5bjP2OBDwmkoWhIDDkic574y04tfzHpn+cJ
odI2D4SseesQ6bDrarZ7C30ddLibZatoKiws3UL9xnELz4ct92vID24FfVbiI1hY
+SW6FoVHkNeWIP0GCbaM4C6uVdF5dTUsMVs/ZbzNnIdCp5Gxmx5ejvEau8otR/Cs
kGN+hr/W5GvT1tMBjgWKZ1i4//emhA1JG1BbPzoLJQvyEotc03lXjTaCzv8mEbep
8RqZ7a2CPsgRbuvTPBwcOMBBmuFeU88+FSBX6+7iP0il8b4Z0QFqIwwMHfs/L6K1
vepuoxtGzi4CZ68zJpiq1UvSqTbFJjtbD4seiMHl
-----END CERTIFICATE-----

-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsFADA5MQsw
CQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6b24gUm9vdCBDQSAx
MB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTELMAkGA1UEBhMCVVMxDzANBgNV
BAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJvb3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBALJ4gHHKeNXjca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOg
Q3pOsqTQNroBvo3bSMgHFzZM9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9
tBb6dNqcmzU5L/qwIFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAw
hmahRWa6VOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L
93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQmjgSubJrI
qg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAYYwHQYDVR0OBBYE
FIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUAA4IBAQCY8jdaQZChGsV2USgg
NiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDIU5PMCCjjmCXPI6T53iHTfIUJrU6adTrC
C2qJeHZERxhlbI1Bjjt/msv0tadQ1wUsN+gDS63pYaACbvXy8MWy7Vu33PqUXHeeE6V/Uq2V
8viTO96LXFvKWlJbYK8U90vvo/ufQJVtMVT8QtPHRh8jrdkPSHCa2XV4cdFyQzR1bldZwgJc
JmApzyMZFo6IQ6XU5MsI+yMRQ+hDKXJioaldXgjUkK642M4UwtBV8ob2xJNDd2ZhwLnoQdeX
eGADbkpyrqXRfboQnoZsG4q5WTP468SQvvG5
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIFQTCCAymgAwIBAgITBmyf0pY1hp8KD+WGePhbJruKNzANBgkqhkiG9w0BAQwFADA5MQsw
CQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6b24gUm9vdCBDQSAy
MB4XDTE1MDUyNjAwMDAwMFoXDTQwMDUyNjAwMDAwMFowOTELMAkGA1UEBhMCVVMxDzANBgNV
BAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJvb3QgQ0EgMjCCAiIwDQYJKoZIhvcNAQEB
BQADggIPADCCAgoCggIBAK2Wny2cSkxKgXlRmeyKy2tgURO8TW0G/LAIjd0ZEGrHJgw12MBv
IITplLGbhQPDW9tK6Mj4kHbZW0/jTOgGNk3Mmqw9DJArktQGGWCsN0R5hYGCrVo34A3MnaZM
UnbqQ523BNFQ9lXg1dKmSYXpN+nKfq5clU1Imj+uIFptiJXZNLhSGkOQsL9sBbm2eLfq0OQ6
PBJTYv9K8nu+NQWpEjTj82R0Yiw9AElaKP4yRLuH3WUnAnE72kr3H9rN9yFVkE8P7K6C4Z9r
2UXTu/Bfh+08LDmG2j/e7HJV63mjrdvdfLC6HM783k81ds8P+HgfajZRRidhW+mez/CiVX18
JYpvL7TFz4QuK/0NURBs+18bvBt+xa47mAExkv8LV/SasrlX6avvDXbR8O70zoan4G7ptGmh
32n2M8ZpLpcTnqWHsFcQgTfJU7O7f/aS0ZzQGPSSbtqDT6ZjmUyl+17vIWR6IF9sZIUVyzfp
YgwLKhbcAS4y2j5L9Z469hdAlO+ekQiG+r5jqFoz7Mt0Q5X5bGlSNscpb/xVA1wf+5+9R+vn
SUeVC06JIglJ4PVhHvG/LopyboBZ/1c6+XUyo05f7O0oYtlNc/LMgRdg7c3r3NunysV+Ar3y
VAhU/bQtCSwXVEqY0VThUWcI0u1ufm8/0i2BWSlmy5A5lREedCf+3euvAgMBAAGjQjBAMA8G
A1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMB0GA1UdDgQWBBSwDPBMMPQFWAJI/TPl
Uq9LhONmUjANBgkqhkiG9w0BAQwFAAOCAgEAqqiAjw54o+Ci1M3m9Zh6O+oAA7CXDpO8Wqj2
LIxyh6mx/H9z/WNxeKWHWc8w4Q0QshNabYL1auaAn6AFC2jkR2vHat+2/XcycuUY+gn0oJMs
XdKMdYV2ZZAMA3m3MSNjrXiDCYZohMr/+c8mmpJ5581LxedhpxfL86kSk5Nrp+gvU5LEYFiw
zAJRGFuFjWJZY7attN6a+yb3ACfAXVU3dJnJUH/jWS5E4ywl7uxMMne0nxrpS10gxdr9HIcW
xkPo1LsmmkVwXqkLN1PiRnsn/eBG8om3zEK2yygmbtmlyTrIQRNg91CMFa6ybRoVGld45pIq
2WWQgj9sAq+uEjonljYE1x2igGOpm/HlurR8FLBOybEfdF849lHqm/osohHUqS0nGkWxr7JO
cQ3AWEbWaQbLU8uz/mtBzUF+fUwPfHJ5elnNXkoOrJupmHN5fLT0zLm4BwyydFy4x2+IoZCn
9Kr5v2c69BoVYh63n749sSmvZ6ES8lgQGVMDMBu4Gon2nL2XA46jCfMdiyHxtN/kHNGfZQIG
6lzWE7OE76KlXIx3KadowGuuQNKotOrN8I1LOJwZmhsoVLiJkO/KdYE+HvJkJMcYr07/R54H
9jVlpNMKVv/1F2Rs76giJUmTtt8AF9pYfl3uxRuw0dFfIRDH+fO6AgonB8Xx1sfT4PsJYGw=
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIBtjCCAVugAwIBAgITBmyf1XSXNmY/Owua2eiedgPySjAKBggqhkjOPQQDAjA5MQswCQYD
VQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6b24gUm9vdCBDQSAzMB4X
DTE1MDUyNjAwMDAwMFoXDTQwMDUyNjAwMDAwMFowOTELMAkGA1UEBhMCVVMxDzANBgNVBAoT
BkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJvb3QgQ0EgMzBZMBMGByqGSM49AgEGCCqGSM49
AwEHA0IABCmXp8ZBf8ANm+gBG1bG8lKlui2yEujSLtf6ycXYqm0fc4E7O5hrOXwzpcVOho6A
F2hiRVd9RFgdszflZwjrZt6jQjBAMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGG
MB0GA1UdDgQWBBSrttvXBp43rDCGB5Fwx5zEGbF4wDAKBggqhkjOPQQDAgNJADBGAiEA4IWS
oxe3jfkrBqWTrBqYaGFy+uGh0PsceGCmQ5nFuMQCIQCcAu/xlJyzlvnrxir4tiz+OpAUFteM
YyRIHN8wfdVoOw==
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIB8jCCAXigAwIBAgITBmyf18G7EEwpQ+Vxe3ssyBrBDjAKBggqhkjOPQQDAzA5MQswCQYD
VQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6b24gUm9vdCBDQSA0MB4X
DTE1MDUyNjAwMDAwMFoXDTQwMDUyNjAwMDAwMFowOTELMAkGA1UEBhMCVVMxDzANBgNVBAoT
BkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJvb3QgQ0EgNDB2MBAGByqGSM49AgEGBSuBBAAi
A2IABNKrijdPo1MN/sGKe0uoe0ZLY7Bi9i0b2whxIdIA6GO9mif78DluXeo9pcmBqqNbIJhF
XRbb/egQbeOc4OO9X4Ri83BkM6DLJC9wuoihKqB1+IGuYgbEgds5bimwHvouXKNCMEAwDwYD
VR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAYYwHQYDVR0OBBYEFNPsxzplbszh2naaVvuc
84ZtV+WBMAoGCCqGSM49BAMDA2gAMGUCMDqLIfG9fhGt0O9Yli/W651+kI0rz2ZVwyzjKKlw
CkcO8DdZEv8tmZQoTipPNU0zWgIxAOp1AE47xDqUEpHJWEadIRNyp4iciuRMStuW1KyLa2tJ
ElMzrdfkviT8tQp21KW8EA==
-----END CERTIFICATE-----
)PEM";
// Select the RSA certificate path before starting the TLS handshake on ESP32 core 3.
// CA chain, hostname and certificate expiry verification remain required.
#if ESP_ARDUINO_VERSION_MAJOR >= 3
class KioskSecureClient : public WiFiClientSecure {
public:
  using WiFiClientSecure::connect;
  int connect(const char *host, uint16_t port, int32_t timeout) override {
    String name(host);
    if (!name.endsWith(".ngrok-free.dev") && !name.endsWith(".ngrok-free.app"))
      return WiFiClientSecure::connect(host, port, timeout);
    setPlainStart();
    if (!WiFiClientSecure::connect(host, port, timeout)) return 0;
    static const int ciphers[] = { MBEDTLS_TLS_RSA_WITH_AES_128_GCM_SHA256, 0 };
    mbedtls_ssl_conf_max_tls_version(&sslclient->ssl_conf, MBEDTLS_SSL_VERSION_TLS1_2);
    mbedtls_ssl_conf_ciphersuites(&sslclient->ssl_conf, ciphers);
    int ret = ssl_starttls_handshake(sslclient.get());
    if (ret >= 0 && mbedtls_ssl_get_verify_result(&sslclient->ssl_ctx) != 0)
      ret = MBEDTLS_ERR_X509_CERT_VERIFY_FAILED;
    sslclient->last_error = ret;
    if (ret < 0) { stop(); return 0; }
    _stillinPlainStart = false;
    Serial.printf("TLS_CIPHER: %s\n", mbedtls_ssl_get_ciphersuite(&sslclient->ssl_ctx));
    return 1;
  }
};
#else
using KioskSecureClient = WiFiClientSecure;
#endif

class TicketKiosk {
  enum class Page { CONFIG, MOVIES, SHOWS, SEATS, CARD, UNKNOWN, TICKET, ERROR, BUSY };
  enum class Recovery { BOOT, MOVIES, SHOWS, SEATS };
  struct Movie { int id; String title; };
  struct Show { int id; String date, time, cinema, room; float price; int available; };
  struct Seat { int id; String row; int number; float price; String status; };
  struct ReceiptTicket { String code, seat; };
  struct Reply { int status = 0; String error; JsonDocument json; };

  static constexpr uint8_t TFT_CS = 5, TFT_DC = 2, TFT_RST = 4;
  static constexpr uint8_t RFID_CS = 15, RFID_RST = 13;
  static constexpr uint8_t RED_PIN = 25, GREEN_PIN = 26, BLUE_PIN = 27, BUZZER = 12;
  static constexpr uint16_t BG = 0x0841, PANEL = 0x18C3, YELLOW = 0xFEA0;
  static constexpr uint16_t WHITE = 0xFFFF, MUTED = 0x9CD3, GREEN = 0x07E0, RED = 0xF920;
  static constexpr int PAGE_SIZE = 4, GRID_ROWS = 7, GRID_COLS = 12;
  static constexpr int MAX_TICKETS = 8;
  static constexpr int GRID_X = 18, GRID_Y = 102, CELL_W = 18, CELL_H = 19;

  Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC, TFT_RST);
  Adafruit_FT6206 touch;
  U8G2_FOR_ADAFRUIT_GFX font;
  MFRC522 rfid = MFRC522(RFID_CS, RFID_RST);
  Preferences prefs;
  Page page = Page::BUSY;
  Recovery recovery = Recovery::MOVIES;
  bool prefsReady = false, touchReady = false, readerReady = false;
  bool touchDown = false, requestBusy = false, paymentPending = false;
  uint32_t lastTouch = 0, lastCountdown = 0, holdDeadline = 0, lastReconnect = 0;
  String apiUrl, apiKey, serialLine, errorMessage, holdId;
  String tlsPin, tlsPinHost;
  std::vector<Movie> movies;
  std::vector<Show> shows;
  std::vector<Seat> seats;
  std::vector<String> seatRows;
  std::vector<int> selectedSeats;
  std::vector<ReceiptTicket> receiptTickets;
  int moviePage = 0, showOffset = 0, showTotal = 0, seatPage = 0;
  int maxSeats = MAX_TICKETS, expectedTickets = 1, ticketIndex = 0;
  Movie selectedMovie;
  Show selectedShow;
  String ticketCode, bookingId, paidSeat, paidTitle, paidDate, paidTime;
  float paidAmount = 0;

public:
  void begin() {
    Serial.begin(115200);
    digitalWrite(TFT_CS, HIGH); pinMode(TFT_CS, OUTPUT);
    digitalWrite(RFID_CS, HIGH); pinMode(RFID_CS, OUTPUT);
    for (uint8_t p : {RED_PIN, GREEN_PIN, BLUE_PIN}) {
      digitalWrite(p, HIGH); pinMode(p, OUTPUT); // Common anode: LOW = on.
    }
    pinMode(BUZZER, OUTPUT); digitalWrite(BUZZER, LOW);
    SPI.begin(18, 19, 23);
    Wire.begin(21, 22);
    tft.begin(); tft.setRotation(0); // Portrait, 240 x 320.
    font.begin(tft); font.setFontMode(1);
    touchReady = touch.begin(40, &Wire);
    prefsReady = prefs.begin("pukankov", false);
    if (prefsReady) {
      apiUrl = prefs.getString("api_url", DEFAULT_API_URL);
      apiKey = prefs.getString("api_key", "");
      tlsPin = prefs.getString("tls_pin", PINNED_CERT_SHA256);
      tlsPinHost = prefs.getString("pin_host", PINNED_API_HOST);
      paymentPending = prefs.getBool("pending", false);
      holdId = prefs.getString("hold", "");
      ticketCode = prefs.getString("ticket", "");
      bookingId = prefs.getString("booking", "");
      paidTitle = prefs.getString("title", "");
      paidDate = prefs.getString("date", "");
      paidTime = prefs.getString("time", "");
      paidSeat = prefs.getString("seat", "");
      paidAmount = prefs.getFloat("amount", 0);
      expectedTickets = prefs.getUInt("seat_count", 1);
      String saved = prefs.getString("receipt", "");
      if (saved.length()) {
        JsonDocument receipt;
        if (deserializeJson(receipt, saved) || !applyReceipt(receipt.as<JsonVariantConst>())) {
          ticketCode = ""; bookingId = "";
          Serial.println("SAVED_RECEIPT_INVALID");
        }
      } else if (validCode(ticketCode) && bookingId.length()) {
        receiptTickets.push_back({ticketCode, paidSeat});
      }
    }
    Serial.println("PUKANKOV KIOSK START");
    Serial.println("Firmware: kiosk-9");
    Serial.println("Commands: KEY <device key> | URL <https URL> | PIN <SHA256> | STATUS | DIAG | RETRY | HELP");
    boot();
  }

  void tick() {
    readSerial();
    if (requestBusy) return;
    if (page == Page::CARD) {
      if ((int32_t)(holdDeadline - millis()) <= 0) {
        String expired = holdId;
        holdId = "";
        api("DELETE", "/api/v1/devices/bookings/holds/" + expired);
        showError("Времето за резервация изтече. Избери мястото отново.", Recovery::SEATS);
        return;
      }
      if (millis() - lastCountdown >= 1000) drawCountdown();
      digitalWrite(TFT_CS, HIGH);
      if (readerReady && rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
        // Reading is the local payment signal. Do not format, print or send UID.
        rfid.PICC_HaltA(); rfid.PCD_StopCrypto1();
        digitalWrite(RFID_CS, HIGH);
        beep(1400, 80);
        if (rememberPending()) submitPayment();
      }
    }
    if (touchReady) {
      bool down = touch.touched() > 0;
      if (down && !touchDown && millis() - lastTouch > 180) {
        TS_Point raw = touch.getPoint();
        int x = constrain(239 - (int)raw.x, 0, 239);
        int y = constrain(319 - (int)raw.y, 0, 319);
        lastTouch = millis();
        touchDown = true;
        onTap(x, y);
      }
      touchDown = down;
    }
    if (WiFi.status() != WL_CONNECTED && millis() - lastReconnect > 15000) {
      lastReconnect = millis(); WiFi.reconnect();
    }
    delay(8);
  }

private:
  void rgb(bool r, bool g, bool b) {
    digitalWrite(RED_PIN, r ? LOW : HIGH);
    digitalWrite(GREEN_PIN, g ? LOW : HIGH);
    digitalWrite(BLUE_PIN, b ? LOW : HIGH);
  }
  void beep(unsigned int hz, unsigned int duration) { tone(BUZZER, hz, duration); }
  void text(const String &s, int x, int baseline, uint16_t color = WHITE, bool large = false, uint16_t background = BG) {
    digitalWrite(RFID_CS, HIGH);
    font.setFont(large ? u8g2_font_9x15_t_cyrillic : u8g2_font_6x13_t_cyrillic);
    font.setFontMode(1); // setFont() resets transparency when the font changes.
    font.setForegroundColor(color); font.setBackgroundColor(background);
    font.setCursor(x, baseline); font.print(s);
  }
  String clipped(const String &s, int maxGlyphs) {
    int glyphs = 0, cut = s.length();
    for (unsigned int i = 0; i < s.length(); i++) {
      if (((uint8_t)s[i] & 0xC0) != 0x80 && ++glyphs > maxGlyphs) { cut = i; break; }
    }
    return cut == (int)s.length() ? s : s.substring(0, cut) + "...";
  }
  void wrapped(String s, int x, int y, int width = 216, uint16_t color = WHITE, int maxLines = 5) {
    String line;
    int lines = 0, chars = width / 6;
    while (s.length() && lines < maxLines) {
      int split = s.indexOf(' ');
      String word = split < 0 ? s : s.substring(0, split);
      s = split < 0 ? "" : s.substring(split + 1);
      String candidate = line.length() ? line + " " + word : word;
      int n = 0;
      for (unsigned int i = 0; i < candidate.length(); i++) if (((uint8_t)candidate[i] & 0xC0) != 0x80) n++;
      if (n > chars && line.length()) {
        text(line, x, y + 17 * lines++, color);
        line = word;
      } else line = candidate;
      if (lines >= maxLines) break;
    }
    if (line.length() && lines < maxLines) text(clipped(line, chars - 3), x, y + 17 * lines, color);
  }
  void frame(const String &title, const String &subtitle = "") {
    digitalWrite(RFID_CS, HIGH);
    tft.fillScreen(BG);
    tft.fillRect(0, 0, 240, 36, PANEL);
    text("ПУКАНКОВ", 12, 25, YELLOW, true);
    tft.fillCircle(224, 18, 4, WiFi.status() == WL_CONNECTED ? GREEN : RED);
    text(title, 10, 56, WHITE, true);
    if (subtitle.length()) text(clipped(subtitle, 34), 10, 74, MUTED);
  }
  void button(int x, int y, int w, const String &label, bool enabled = true, bool primary = false) {
    uint16_t fill = enabled && primary ? YELLOW : PANEL;
    tft.fillRoundRect(x, y, w, 32, 5, fill);
    tft.drawRoundRect(x, y, w, 32, 5, enabled ? (primary ? YELLOW : MUTED) : 0x3186);
    text(label, x + 6, y + 21, enabled ? (primary ? BG : WHITE) : 0x528A, false, fill);
  }
  bool inside(int x, int y, int bx, int by, int bw, int bh = 32) {
    return x >= bx && x < bx + bw && y >= by && y < by + bh;
  }
  void busy(const String &message) {
    page = Page::BUSY; rgb(false, false, true);
    frame("Моля, изчакай"); wrapped(message, 12, 108);
  }
  void showError(const String &message, Recovery action) {
    errorMessage = message; recovery = action; page = Page::ERROR;
    rgb(true, false, false); beep(400, 120);
    frame("Неуспешна операция"); wrapped(message, 12, 96, 216, WHITE, 8);
    button(8, 280, 108, "Повтори", true, true);
    button(124, 280, 108, "Филми", !paymentPending);
    Serial.println("KIOSK_ERROR: " + message);
  }
  void configScreen() {
    page = Page::CONFIG; rgb(false, false, true);
    frame("Настройване");
    wrapped("В Serial Monitor изпрати KEY и ключа за терминала, разделени с интервал.", 12, 100);
    wrapped("За нов адрес: URL https://...", 12, 210);
    text("Ключът не се показва на екрана.", 12, 270, MUTED);
    Serial.println("CONFIG_REQUIRED: send KEY <device key>");
  }
  void readSerial() {
    while (Serial.available()) {
      char c = (char)Serial.read();
      if (c == '\r') continue;
      if (c == '\n') {
        String cmd = serialLine; serialLine = ""; cmd.trim();
        if (cmd.startsWith("KEY ")) {
          String key = cmd.substring(4); key.trim();
          if (key.length() < 20 || key.indexOf(' ') >= 0 || !prefsReady) {
            Serial.println("Invalid key or unavailable NVS."); continue;
          }
          apiKey = key; prefs.putString("api_key", apiKey);
          Serial.println("Device key saved (not echoed)."); boot();
        } else if (cmd.startsWith("URL ")) {
          String url = cmd.substring(4); url.trim();
          while (url.endsWith("/")) url.remove(url.length() - 1);
          if (!url.startsWith("https://") || url.indexOf(' ') >= 0 || !prefsReady) {
            Serial.println("Use URL https://hostname without a trailing API path."); continue;
          }
          apiUrl = url; prefs.putString("api_url", apiUrl);
          Serial.println("API URL saved."); boot();
        } else if (cmd.startsWith("PIN ")) {
          String pin = cmd.substring(4); pin.trim(); pin.replace(":", ""); pin.replace(" ", ""); pin.toLowerCase();
          bool valid = pin.length() == 64 && prefsReady;
          for (unsigned int i = 0; i < pin.length(); i++) {
            if (!((pin[i] >= '0' && pin[i] <= '9') || (pin[i] >= 'a' && pin[i] <= 'f'))) valid = false;
          }
          String host = apiUrl.substring(8);
          if (!valid || host.indexOf('/') >= 0 || host.indexOf(':') >= 0) {
            Serial.println("Use PIN followed by 64 SHA256 hex characters from START-STABLE-API.cmd."); continue;
          }
          if (!prefs.putString("tls_pin", pin) || !prefs.putString("pin_host", host)) {
            Serial.println("Could not save certificate pin."); continue;
          }
          tlsPin = pin; tlsPinHost = host;
          Serial.println("Certificate pin saved for " + host); boot();
        } else if (cmd == "STATUS") {
          printNetworkStatus();
        } else if (cmd == "DIAG") {
          printNetworkStatus();
          Reply health = api("GET", "/api/v1/health");
          Serial.printf("DIAG_HEALTH: HTTP %d\n", health.status);
          if (health.error.length()) Serial.println(health.error);
        } else if (cmd == "RETRY") {
          boot();
        } else if (cmd.length()) Serial.println("Commands: KEY <key> | URL <https base URL> | PIN <SHA256> | STATUS | DIAG | RETRY | HELP");
      } else if (serialLine.length() < 512) serialLine += c;
      else serialLine = "";
    }
  }
  void printNetworkStatus() {
    Serial.printf("API_BASE: %s\n", apiUrl.c_str());
    Serial.printf("KEY_CONFIGURED: %s; PAYMENT_PENDING: %s\n",
                  apiKey.length() >= 20 ? "yes" : "no", paymentPending ? "yes" : "no");
    Serial.printf("WIFI_STATUS: %d; IP: %s; DNS: %s\n", (int)WiFi.status(),
                  WiFi.localIP().toString().c_str(), WiFi.dnsIP().toString().c_str());
    time_t now = time(nullptr);
    struct tm utc;
    gmtime_r(&now, &utc);
    char stamp[32];
    strftime(stamp, sizeof(stamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
    Serial.printf("UTC: %s; FREE_HEAP: %u\n", stamp, (unsigned)ESP.getFreeHeap());
  }
  bool connectNetwork() {
    if (WiFi.status() != WL_CONNECTED) {
      busy("Свързване с WiFi...");
      WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);
      uint32_t start = millis();
      while (WiFi.status() != WL_CONNECTED && millis() - start < 25000) { delay(250); }
      if (WiFi.status() != WL_CONNECTED) {
        Serial.printf("WIFI_FAILED: status=%d\n", (int)WiFi.status());
        return false;
      }
    }
    if (time(nullptr) < 1700000000) {
      busy("Сверяване на часовника за защитена връзка...");
      configTime(0, 0, "pool.ntp.org", "time.nist.gov");
      uint32_t start = millis();
      while (time(nullptr) < 1700000000 && millis() - start < 20000) delay(200);
      if (time(nullptr) < 1700000000) {
        Serial.println("NTP_FAILED: HTTPS requires a synchronized clock.");
        return false;
      }
    }
    printNetworkStatus();
    return true;
  }
  void boot() {
    if (!prefsReady) { showError("NVS паметта не е достъпна. Рестартирай симулацията.", Recovery::BOOT); return; }
    if (!touchReady) { showError("Touch контролерът липсва. Провери SDA 21 и SCL 22.", Recovery::BOOT); return; }
    if (apiKey.length() < 20) { configScreen(); return; }
    busy("Проверка на RFID четеца...");
    digitalWrite(TFT_CS, HIGH); rfid.PCD_Init();
    byte version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
    readerReady = version != 0 && version != 0xFF;
    if (!connectNetwork()) {
      showError("Няма WiFi или точен часовник. Провери връзката и опитай отново.", Recovery::BOOT); return;
    }
    if (paymentPending && holdId.length()) { drawUnknown("Възстановена незавършена заявка. Провери същата поръчка."); return; }
    if (ticketCode.length() == 6 && bookingId.length()) { drawTicket(); return; }
    loadMovies();
  }
  Reply api(const char *method, const String &path, const String &body = "") {
    Reply reply;
    requestBusy = true;
    if (WiFi.status() != WL_CONNECTED) {
      reply.error = "Няма WiFi връзка."; requestBusy = false; return reply;
    }
    digitalWrite(TFT_CS, HIGH); digitalWrite(RFID_CS, HIGH);
    String host = apiUrl.substring(8);
    int slash = host.indexOf('/');
    if (slash >= 0) host = host.substring(0, slash);
    IPAddress resolved;
    if (!WiFi.hostByName(host.c_str(), resolved)) {
      Serial.printf("DNS_FAILED: %s\n", host.c_str());
      reply.error = "DNS_FAILED: Wokwi не намира API адреса. Провери URL и тунела.";
      requestBusy = false; return reply;
    }
    Serial.printf("DNS_OK: %s -> %s\n", host.c_str(), resolved.toString().c_str());
    KioskSecureClient client;
    bool pinMode = host == tlsPinHost && tlsPin.length() == 64;
    if (pinMode) {
      // CA chain processing is deferred to the trusted PC launcher. Authenticate
      // the exact peer certificate below BEFORE adding any HTTP credentials.
      client.setInsecure();
    } else client.setCACert(ROOT_CA);
    client.setHandshakeTimeout(30);
    Serial.println(pinMode ? "TLS_CONNECT: SHA256 certificate pin authentication" : "TLS_CONNECT: CA verification");
    // Connect explicitly to preserve the TLS error before HTTPClient closes the socket.
    // Keep the hostname here: certificate verification and SNI require it.
    if (!client.connect(host.c_str(), 443, 30000)) {
      char tlsMessage[192] = {};
      int tlsCode = client.lastError(tlsMessage, sizeof(tlsMessage));
      Serial.printf("TLS_FAILED: code=%d; %s\n", tlsCode, tlsMessage);
      printNetworkStatus();
      reply.error = "TLS_FAILED: HTTPS връзката не е установена. Изпрати TLS_FAILED от Serial Monitor.";
      requestBusy = false; return reply;
    }
    if (pinMode) {
      uint8_t fingerprint[32];
      const mbedtls_x509_crt *peer = client.getPeerCertificate();
      bool verified = peer && client.getFingerprintSHA256(fingerprint);
      char hex[65] = {};
      if (verified) {
        for (int i = 0; i < 32; i++) snprintf(hex + 2 * i, 3, "%02x", fingerprint[i]);
        verified = tlsPin == hex && !mbedtls_x509_time_is_past(&peer->valid_to)
                   && !mbedtls_x509_time_is_future(&peer->valid_from);
      }
      if (!verified) {
        client.stop();
        Serial.println("TLS_PIN_FAILED: no HTTP request or API key was sent.");
        reply.error = "Сертификатът не съвпада или е изтекъл. Провери PIN през START-STABLE-API.cmd.";
        requestBusy = false; return reply;
      }
      Serial.println("TLS_PIN_OK");
    }
    Serial.println("TLS_OK");
    HTTPClient http; http.setConnectTimeout(30000); http.setTimeout(30000);
    const char *wanted[] = {"X-Total-Count"};
    if (!http.begin(client, host, 443, path, true)) {
      reply.error = "Невалиден API адрес."; requestBusy = false; return reply;
    }
    http.collectHeaders(wanted, 1);
    http.addHeader("Authorization", "Bearer " + apiKey);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Accept", "application/json");
    reply.status = http.sendRequest(method, body);
    if (reply.status > 0) {
      String response = http.getString();
      DeserializationError err = deserializeJson(reply.json, response);
      if (err) reply.error = "Отговорът не е валиден JSON. Провери адреса на тунела.";
      else if (reply.status >= 400) {
        JsonVariant detail = reply.json["detail"];
        if (detail.is<const char *>()) reply.error = detail.as<String>();
        else if (detail["message"].is<const char *>()) reply.error = detail["message"].as<String>();
        else reply.error = "API грешка HTTP " + String(reply.status);
      }
      if (String(method) == "GET" && path.startsWith("/api/v1/devices/showtimes?")) {
        showTotal = http.header("X-Total-Count").toInt();
      }
    } else {
      Serial.printf("HTTP_TRANSPORT_ERROR: %s\n", HTTPClient::errorToString(reply.status).c_str());
      reply.error = "Няма HTTP отговор след HTTPS свързването. Изпрати HTTP_TRANSPORT_ERROR от Serial Monitor.";
    }
    Serial.printf("HTTP %d %s %s\n", reply.status, method, path.c_str());
    http.end(); requestBusy = false;
    return reply;
  }
  void loadMovies() {
    busy("Зареждане на филмите...");
    Reply r = api("GET", "/api/v1/devices/movies");
    if (r.status != 200 || r.error.length() || !r.json.is<JsonArray>()) {
      showError(r.error.length() ? r.error : "Не успяхме да заредим филмите.", Recovery::MOVIES); return;
    }
    movies.clear();
    for (JsonObject m : r.json.as<JsonArray>()) movies.push_back({m["id"].as<int>(), m["title"].as<String>()});
    moviePage = 0; drawMovies(); Serial.println("READY_MOVIES");
  }
  void drawMovies() {
    page = Page::MOVIES; rgb(false, false, false);
    frame("1. Избери филм", String(movies.size()) + " филма с прожекции");
    if (movies.empty()) wrapped("Няма бъдещи прожекции. Обнови програмата по-късно.", 12, 110);
    for (int i = 0; i < PAGE_SIZE; i++) {
      int n = moviePage * PAGE_SIZE + i;
      if (n >= (int)movies.size()) break;
      int y = 84 + i * 43;
      tft.fillRoundRect(8, y, 224, 38, 5, PANEL);
      text(clipped(movies[n].title, 32), 15, y + 24, WHITE);
    }
    button(8, 280, 70, "< Назад", moviePage > 0);
    button(86, 280, 68, "Обнови");
    button(162, 280, 70, "Напред >", (moviePage + 1) * PAGE_SIZE < (int)movies.size());
  }
  void loadShows() {
    busy("Зареждане на датите и часовете...");
    Reply r = api("GET", "/api/v1/devices/showtimes?movie_id=" + String(selectedMovie.id) + "&limit=4&offset=" + String(showOffset));
    if (r.status != 200 || r.error.length() || !r.json.is<JsonArray>()) {
      showError(r.error.length() ? r.error : "Няма програма.", Recovery::SHOWS); return;
    }
    shows.clear();
    for (JsonObject s : r.json.as<JsonArray>()) shows.push_back({s["id"].as<int>(), s["date"].as<String>(), s["time"].as<String>(), s["cinema"].as<String>(), s["auditorium"].as<String>(), s["price"].as<float>(), s["available_seats"].as<int>()});
    if (showTotal < showOffset + (int)shows.size()) showTotal = showOffset + shows.size();
    drawShows(); Serial.println("READY_SHOWTIMES");
  }
  void drawShows() {
    page = Page::SHOWS; rgb(false, false, false);
    frame("2. Избери час", selectedMovie.title);
    if (shows.empty()) wrapped("Няма бъдещи прожекции за този филм.", 12, 110);
    for (int i = 0; i < (int)shows.size(); i++) {
      int y = 84 + i * 43;
      tft.fillRoundRect(8, y, 224, 39, 5, PANEL);
      text(shows[i].date + "  " + shows[i].time, 14, y + 15, shows[i].available ? YELLOW : MUTED);
      text(clipped(shows[i].cinema, 21) + " | " + String(shows[i].available), 14, y + 31, MUTED);
    }
    button(8, 280, 56, "Филми"); button(70, 280, 40, "<", showOffset > 0);
    button(116, 280, 68, "Обнови"); button(190, 280, 42, ">", showOffset + PAGE_SIZE < showTotal);
  }
  void loadSeats() {
    busy("Проверка на свободните места...");
    Reply r = api("GET", "/api/v1/devices/showtimes/" + String(selectedShow.id) + "/seats");
    if (r.status != 200 || r.error.length() || !r.json["seats"].is<JsonArray>()) {
      showError(r.error.length() ? r.error : "Местата не са достъпни.", Recovery::SEATS); return;
    }
    seats.clear(); seatRows.clear(); selectedSeats.clear(); seatPage = 0;
    int limit = r.json["max_seats"] | MAX_TICKETS;
    maxSeats = limit > 0 && limit < MAX_TICKETS ? limit : MAX_TICKETS;
    for (JsonObject s : r.json["seats"].as<JsonArray>()) {
      seats.push_back({s["id"].as<int>(), s["row"].as<String>(), s["number"].as<int>(), s["price"].as<float>(), s["status"].as<String>()});
      bool found = false;
      for (const String &row : seatRows) if (row == seats.back().row) found = true;
      if (!found) seatRows.push_back(seats.back().row);
    }
    drawSeats(); Serial.println("READY_SEATS");
  }
  void drawSeats() {
    page = Page::SEATS; rgb(false, false, false);
    frame("3. Избери места", selectedShow.date + " " + selectedShow.time);
    text("<", 8, 92, seatPage > 0 ? YELLOW : MUTED);
    text("ЕКРАН", 100, 92, MUTED);
    text(">", 222, 92, (seatPage + 1) * GRID_ROWS < (int)seatRows.size() ? YELLOW : MUTED);
    for (int row = 0; row < GRID_ROWS; row++) {
      int n = seatPage * GRID_ROWS + row;
      if (n >= (int)seatRows.size()) break;
      text(seatRows[n], 2, GRID_Y + row * CELL_H + 14, MUTED);
      for (int i = 0; i < (int)seats.size(); i++) {
        const Seat &s = seats[i];
        if (s.row != seatRows[n] || s.number < 1 || s.number > GRID_COLS) continue;
        int x = GRID_X + (s.number - 1) * CELL_W, y = GRID_Y + row * CELL_H;
        uint16_t color = s.status == "available" ? GREEN : (s.status == "held" ? 0xFD20 : 0x526A);
        if (isSelected(i)) color = YELLOW;
        tft.fillRoundRect(x, y, CELL_W - 2, CELL_H - 2, 2, color);
        text(String(s.number), x + 1, y + 13, BG, false, color);
      }
    }
    text("Избрани " + String(selectedSeats.size()) + "/" + String(maxSeats) + " | " + String(selectedTotal(), 2) + " EUR", 10, 251, YELLOW);
    text(selectedSeats.empty() ? "Докосни място за избор / отказ." : clipped(selectionLabel(), 35), 10, 269, MUTED);
    button(8, 280, 68, "Часове"); button(82, 280, 62, "Обнови");
    button(150, 280, 82, "Продължи", !selectedSeats.empty(), true);
  }
  bool isSelected(int index) {
    for (int selected : selectedSeats) if (selected == index) return true;
    return false;
  }
  float selectedTotal() {
    float total = 0;
    for (int index : selectedSeats) total += seats[index].price;
    return total;
  }
  String selectionLabel() {
    String label;
    for (int index : selectedSeats) {
      if (label.length()) label += " ";
      label += seats[index].row + String(seats[index].number);
    }
    return label;
  }
  void toggleSeat(int index) {
    for (unsigned int i = 0; i < selectedSeats.size(); i++) {
      if (selectedSeats[i] == index) { selectedSeats.erase(selectedSeats.begin() + i); drawSeats(); return; }
    }
    if ((int)selectedSeats.size() >= maxSeats) {
      beep(400, 100);
      tft.fillRect(0, 254, 240, 21, BG);
      text("Максимум " + String(maxSeats) + " места в покупка.", 10, 269, YELLOW);
      return;
    }
    if (index < 0 || index >= (int)seats.size() || seats[index].status != "available") return;
    selectedSeats.push_back(index); drawSeats();
  }
  time_t isoTime(const String &s) {
    int y, m, d, h, minute, sec;
    if (sscanf(s.c_str(), "%d-%d-%dT%d:%d:%d", &y, &m, &d, &h, &minute, &sec) != 6) return 0;
    struct tm t = {}; t.tm_year = y - 1900; t.tm_mon = m - 1; t.tm_mday = d;
    t.tm_hour = h; t.tm_min = minute; t.tm_sec = sec; t.tm_isdst = 0;
    return mktime(&t); // configTime(0,0,...) keeps the local zone UTC.
  }
  void reserveSeat() {
    if (selectedSeats.empty()) return;
    if (!readerReady) {
      showError("RFID четецът не е готов. Провери кабелите и рестартирай.", Recovery::BOOT); return;
    }
    busy("Задържане на избраните места за 5 минути...");
    JsonDocument body; body["showtime_id"] = selectedShow.id;
    JsonArray ids = body["seat_ids"].to<JsonArray>();
    for (int index : selectedSeats) ids.add(seats[index].id);
    String payload; serializeJson(body, payload);
    Reply r = api("POST", "/api/v1/devices/bookings/holds", payload);
    if (r.status != 201 || r.error.length() || !r.json["id"].is<const char *>()) {
      showError(r.error.length() ? r.error : "Мястото вече не е свободно. Обнови схемата.", Recovery::SEATS); return;
    }
    holdId = r.json["id"].as<String>();
    long ttl = (long)(isoTime(r.json["expires_at"].as<String>()) - isoTime(r.json["server_time"].as<String>()));
    if (ttl <= 0) ttl = 1;
    if (ttl > 3600) ttl = 3600;
    holdDeadline = millis() + (uint32_t)(ttl > 2 ? ttl - 2 : ttl) * 1000;
    paidTitle = selectedMovie.title; paidDate = selectedShow.date; paidTime = selectedShow.time;
    paidSeat = selectionLabel(); paidAmount = r.json["total"].as<float>();
    expectedTickets = selectedSeats.size();
    drawCard(); Serial.println("READY_RFID");
  }
  void drawCard() {
    page = Page::CARD; rgb(true, true, false);
    frame("4. Доближи карта", "RFID се чете само на ESP32");
    wrapped(paidTitle, 12, 103, 216, WHITE, 2);
    text(paidDate + "  " + paidTime, 12, 148, MUTED);
    wrapped("Места: " + paidSeat, 12, 171, 216, WHITE, 2);
    text(String(paidAmount, 2) + " EUR", 12, 205, YELLOW, true);
    text("Оставащо време:", 12, 243, MUTED);
    button(8, 280, 224, "Откажи резервацията");
    drawCountdown();
  }
  void drawCountdown() {
    lastCountdown = millis();
    long seconds = (int32_t)(holdDeadline - millis()) / 1000;
    if (seconds < 0) seconds = 0;
    char timer[12]; snprintf(timer, sizeof(timer), "%02ld:%02ld", seconds / 60, seconds % 60);
    tft.fillRect(158, 226, 76, 27, BG); text(timer, 168, 244, YELLOW, true);
  }
  bool rememberPending() {
    bool holdSaved = prefs.putString("hold", holdId) > 0;
    prefs.putString("title", paidTitle);
    prefs.putString("date", paidDate); prefs.putString("time", paidTime);
    prefs.putString("seat", paidSeat); prefs.putFloat("amount", paidAmount);
    bool countSaved = prefs.putUInt("seat_count", expectedTickets) == sizeof(uint32_t);
    if (!holdSaved || !countSaved || prefs.putBool("pending", true) != 1) {
      showError("Поръчката не може да се запази в паметта. Не е изпратено плащане.", Recovery::SEATS); return false;
    }
    paymentPending = true;
    Serial.println("PAYMENT_PENDING"); return true;
  }
  void drawUnknown(const String &message) {
    page = Page::UNKNOWN; rgb(true, true, false);
    frame("Проверка на плащане"); wrapped(message, 12, 100, 216, WHITE, 8);
    text("Не започвай втора покупка.", 12, 250, MUTED);
    button(8, 280, 224, "Повтори същата заявка", true, true);
    Serial.println("PAYMENT_UNKNOWN");
  }
  void submitPayment() {
    busy("Изпращане на успешното RFID четене...");
    JsonDocument body; body["hold_id"] = holdId; body["payment_success"] = true;
    String payload; serializeJson(body, payload);
    Reply r = api("POST", "/api/v1/devices/payments/checkout", payload);
    if (r.status == 200 && !r.error.length() && r.json["success"].is<bool>()) {
      if (r.json["success"].as<bool>()) {
        std::vector<ReceiptTicket> verified;
        if (!decodeTickets(r.json["tickets"], verified) || (int)verified.size() != expectedTickets
            || !r.json["booking_id"].is<const char *>() || !r.json["booking_id"].as<String>().length()) {
          drawUnknown("Билетите не са потвърдени изцяло. Провери същата поръчка."); return;
        }
        // Persist the complete receipt as one NVS value before clearing pending.
        String saved; serializeJson(r.json, saved);
        if (prefs.putString("receipt", saved) != saved.length() || prefs.putBool("pending", false) != 1) {
          drawUnknown("Билетите не са запазени в паметта. Провери същата поръчка."); return;
        }
        applyReceipt(r.json.as<JsonVariantConst>());
        paymentPending = false; holdId = "";
        rgb(false, true, false); beep(1800, 180); drawTicket();
        for (const ReceiptTicket &t : receiptTickets) Serial.println("TICKET_CODE=" + t.code + " SEAT=" + t.seat);
        return;
      }
      if (!r.json["success"].as<bool>()) {
        prefs.putBool("pending", false); paymentPending = false; holdId = "";
        showError("Поръчката е отказана. Не е издаден билет. Избери място отново.", Recovery::SEATS); return;
      }
    }
    if (r.status == 409) {
      prefs.putBool("pending", false); paymentPending = false; holdId = "";
      showError(r.error.length() ? r.error : "Резервацията е изтекла.", Recovery::SEATS); return;
    }
    drawUnknown(r.error.length() ? r.error : "Резултатът не е потвърден. Повтори същата заявка.");
  }
  bool validCode(const String &code) {
    if (code.length() != 6) return false;
    for (unsigned int i = 0; i < code.length(); i++) if (code[i] < '0' || code[i] > '9') return false;
    return true;
  }
  bool decodeTickets(JsonVariantConst value, std::vector<ReceiptTicket> &result) {
    if (!value.is<JsonArrayConst>()) return false;
    JsonArrayConst items = value.as<JsonArrayConst>();
    if (!items.size() || items.size() > MAX_TICKETS) return false;
    result.clear();
    for (JsonObjectConst item : items) {
      if (!item["ticket_code"].is<const char *>() || !item["seat"].is<const char *>()) return false;
      String code = item["ticket_code"].as<String>(), seat = item["seat"].as<String>();
      if (!validCode(code) || !seat.length()) return false;
      for (const ReceiptTicket &previous : result) if (previous.code == code || previous.seat == seat) return false;
      result.push_back({code, seat});
    }
    return true;
  }
  bool applyReceipt(JsonVariantConst receipt) {
    std::vector<ReceiptTicket> verified;
    if (!receipt["booking_id"].is<const char *>() || !receipt["booking_id"].as<String>().length()
        || !decodeTickets(receipt["tickets"], verified)) return false;
    receiptTickets = verified; ticketIndex = 0; expectedTickets = receiptTickets.size();
    ticketCode = receiptTickets[0].code; bookingId = receipt["booking_id"].as<String>();
    paidTitle = receipt["movie"].as<String>(); paidDate = receipt["date"].as<String>();
    paidTime = receipt["showtime"].as<String>(); paidAmount = receipt["amount"].as<float>();
    paidSeat = "";
    for (const ReceiptTicket &t : receiptTickets) { if (paidSeat.length()) paidSeat += " "; paidSeat += t.seat; }
    return true;
  }
  void drawTicket() {
    if (receiptTickets.empty()) return;
    const ReceiptTicket &ticket = receiptTickets[ticketIndex];
    ticketCode = ticket.code;
    page = Page::TICKET; rgb(false, true, false);
    frame("Билет " + String(ticketIndex + 1) + "/" + String(receiptTickets.size())); wrapped(paidTitle, 12, 92, 216, WHITE, 2);
    text(paidDate + "  " + paidTime, 12, 139, MUTED);
    text("Място " + ticket.seat, 12, 164, WHITE, true);
    tft.fillRoundRect(8, 184, 224, 64, 7, YELLOW);
    tft.setTextColor(BG); tft.setTextSize(4); tft.setCursor(47, 201); tft.print(ticketCode); tft.setTextSize(1);
    text("Въведи кода на входа.", 12, 266, MUTED);
    button(8, 280, 36, "<", ticketIndex > 0);
    button(50, 280, 140, "Нова покупка", true, true);
    button(196, 280, 36, ">", ticketIndex + 1 < (int)receiptTickets.size());
    Serial.println("READY_TICKET");
  }
  void cancelHold() {
    busy("Освобождаване на мястото...");
    Reply r = api("DELETE", "/api/v1/devices/bookings/holds/" + holdId);
    if (r.status == 200 && !r.error.length()) {
      if (r.json["status"] == "completed") { if (rememberPending()) submitPayment(); return; }
      holdId = ""; loadSeats(); return;
    }
    // No payment has been sent yet; preserve the hold and let the user retry.
    drawCard(); text("Няма връзка. Опитай отново.", 12, 268, RED);
  }
  void onTap(int x, int y) {
    if (page == Page::BUSY || page == Page::CONFIG) return;
    beep(1000, 25);
    if (page == Page::UNKNOWN) { if (y >= 280) submitPayment(); return; }
    if (page == Page::TICKET) {
      if (inside(x,y,8,280,36) && ticketIndex > 0) { ticketIndex--; drawTicket(); }
      else if (inside(x,y,196,280,36) && ticketIndex + 1 < (int)receiptTickets.size()) { ticketIndex++; drawTicket(); }
      else if (inside(x,y,50,280,140)) {
        ticketCode = ""; bookingId = ""; receiptTickets.clear(); ticketIndex = 0;
        prefs.remove("receipt"); prefs.remove("ticket"); prefs.remove("booking"); loadMovies();
      }
      return;
    }
    if (page == Page::ERROR) {
      if (inside(x,y,8,280,108)) {
        if (recovery == Recovery::BOOT) boot();
        else if (recovery == Recovery::SHOWS) loadShows();
        else if (recovery == Recovery::SEATS && selectedShow.id > 0) loadSeats();
        else loadMovies();
      } else if (inside(x,y,124,280,108) && !paymentPending) loadMovies();
      return;
    }
    if (page == Page::MOVIES) {
      for (int i=0;i<PAGE_SIZE;i++) if (inside(x,y,8,84+i*43,224,38)) {
        int n=moviePage*PAGE_SIZE+i;
        if(n<(int)movies.size()){selectedMovie=movies[n];showOffset=0;loadShows();} return;
      }
      if (inside(x,y,8,280,70) && moviePage>0) {moviePage--;drawMovies();}
      else if (inside(x,y,86,280,68)) loadMovies();
      else if (inside(x,y,162,280,70) && (moviePage+1)*PAGE_SIZE<(int)movies.size()) {moviePage++;drawMovies();}
      return;
    }
    if (page == Page::SHOWS) {
      for(int i=0;i<(int)shows.size();i++) if(inside(x,y,8,84+i*43,224,39)) {
        if(shows[i].available>0){selectedShow=shows[i];loadSeats();} return;
      }
      if(inside(x,y,8,280,56)) drawMovies();
      else if(inside(x,y,70,280,40)&&showOffset>0){showOffset-=PAGE_SIZE;loadShows();}
      else if(inside(x,y,116,280,68)) loadShows();
      else if(inside(x,y,190,280,42)&&showOffset+PAGE_SIZE<showTotal){showOffset+=PAGE_SIZE;loadShows();}
      return;
    }
    if (page == Page::SEATS) {
      if(y>=80&&y<98) {
        if(x<40&&seatPage>0){seatPage--;drawSeats();}
        else if(x>200&&(seatPage+1)*GRID_ROWS<(int)seatRows.size()){seatPage++;drawSeats();}
        return;
      }
      if(x>=GRID_X&&x<GRID_X+GRID_COLS*CELL_W&&y>=GRID_Y&&y<GRID_Y+GRID_ROWS*CELL_H){
        int row=seatPage*GRID_ROWS+(y-GRID_Y)/CELL_H;
        int number=(x-GRID_X)/CELL_W+1;
        if(row<(int)seatRows.size())for(int i=0;i<(int)seats.size();i++)
          if(seats[i].row==seatRows[row]&&seats[i].number==number&&seats[i].status=="available"){toggleSeat(i);break;}
        return;
      }
      if(inside(x,y,8,280,68)) drawShows();
      else if(inside(x,y,82,280,62)) loadSeats();
      else if(inside(x,y,150,280,82)&&!selectedSeats.empty()) reserveSeat();
      return;
    }
    if(page==Page::CARD&&inside(x,y,8,280,224))cancelHold();
  }
};

TicketKiosk kiosk;
void setup() { kiosk.begin(); }
void loop() { kiosk.tick(); }
