#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <AccelStepper.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <stdio.h>
#include <string.h>
// ============================================================
// PUKANKOV MACHINE — VERSION 2.0
// Board: Arduino Mega 2560
// Simulation: Wokwi
//
// Libraries:
// MFRC522, AccelStepper, LiquidCrystal I2C
// ============================================================
// --------------------------- CONFIG ---------------------------
namespace Config {
  constexpr uint8_t LCD_ADDRESS = 0x27;
  constexpr uint8_t LCD_COLS = 20;
  constexpr uint8_t LCD_ROWS = 4;
  constexpr uint8_t RFID_SS  = 53;
  constexpr uint8_t RFID_RST = 40;
  constexpr uint8_t JOY_Y = A0;
  constexpr uint8_t JOY_X = A1;
  constexpr uint8_t JOY_SW = 34;
  constexpr uint8_t BUZZER = 5;
  constexpr uint8_t LED_R = 9;
  constexpr uint8_t LED_G = 10;
  constexpr uint8_t LED_B = 11;
  constexpr uint8_t SERVO_CORN    = 2;
  constexpr uint8_t SERVO_MACHINE = 3;
  constexpr uint8_t SERVO_POPCORN = 6;
  constexpr uint8_t SERVO_NACHOS  = 4;
  constexpr uint8_t CORN_CLOSED = 0;
  constexpr uint8_t CORN_OPEN   = 90;
  constexpr uint8_t MACHINE_OFF = 0;
  constexpr uint8_t MACHINE_ON  = 90;
  constexpr uint8_t DISPENSER_CLOSED = 0;
  constexpr uint8_t DISPENSER_OPEN   = 90;
  // Common-anode LED: COM е свързан към +5 V.
  constexpr bool COMMON_ANODE = true;
  // UI timing
  constexpr unsigned long NAV_REPEAT_MS = 220;
  constexpr unsigned long BUTTON_DEBOUNCE_MS = 35;
  constexpr unsigned long SCREEN_REFRESH_MS = 150;
  // RFID
  constexpr unsigned long PAYMENT_TIMEOUT_MS = 60000;
  // Production
  constexpr unsigned long CORN_LOADING_MS = 1000;
  constexpr unsigned long POPPING_MS = 180000;
  // За тестове можеш временно да смениш POPPING_MS на 5000.
  // Popcorn inventory is tracked by weight in grams.
  constexpr float POPCORN_BATCH_G = 3500.0f;       // 3.5 kg per batch
  constexpr float POPCORN_REORDER_BELOW_G = 5000.0f; // reorder below 5 kg
  constexpr float POPCORN_INITIAL_G = 50000.0f;      // start with 50 kg
  constexpr float POPCORN_MAX_G = 50000.0f;          // maximum 50 kg
  // Примерни времена, които се калибрират спрямо дозатора.
  constexpr unsigned long POPCORN_TIME_MS[3] = {
    800, 1300, 1800
  };
  constexpr unsigned long NACHOS_TIME_MS[3] = {
    800, 1300, 1900
  };
  // Начални времена за помпите.
  // Не са гарантирани реални дебити.
  constexpr unsigned long DRINK_TIME_MS[3] = {
    10000, 16000, 20000
  };
  // Simulated serving weights; calibrate against the real dispenser.
  constexpr float POPCORN_SERVING_G[3] = {
    150.0f, 250.0f, 350.0f
  };
  constexpr float NACHOS_SERVING_G[3] = {
    50.0f, 80.0f, 120.0f
  };
  constexpr uint16_t DRINK_SERVING_ML[3] = {
    250, 400, 500
  };
  // Prices in EUR, converted from the original BGN values.
  constexpr float POPCORN_PRICE[3] = {1.02f, 1.53f, 2.05f};
  constexpr float DRINK_PRICE[3] = {1.02f, 1.28f, 1.53f};
  constexpr float NACHOS_PRICE[3] = {1.02f, 1.53f, 2.05f};
  constexpr float INITIAL_NACHOS_G = 15000.0f; // 15 kg
  // Each beverage tank starts with 500 litres (values stored in ml).
  constexpr float DRINK_TANK_ML = 500000.0f;
  // Скорост на stepper моторите — начална настройка.
  constexpr float PUMP_SPEED = 400.0f;
}
// --------------------------- HARDWARE -------------------------
LiquidCrystal_I2C lcd(
  Config::LCD_ADDRESS,
  Config::LCD_COLS,
  Config::LCD_ROWS
);
MFRC522 rfid(
  Config::RFID_SS,
  Config::RFID_RST
);
Servo servoCorn;
Servo servoMachine;
Servo servoPopcorn;
Servo servoNachos;
AccelStepper pumpCoke(
  AccelStepper::DRIVER, 27, 24
);
AccelStepper pumpFanta(
  AccelStepper::DRIVER, 49, 47
);
AccelStepper pumpSprite(
  AccelStepper::DRIVER, 43, 46
);
AccelStepper pumpWater(
  AccelStepper::DRIVER, 45, 44
);
// --------------------------- TYPES ----------------------------
enum class Product : uint8_t {
  Popcorn,
  Coke,
  Fanta,
  Sprite,
  Water,
  Nachos
};
enum class ServingSize : uint8_t {
  Small,
  Medium,
  Large
};
enum class UiState : uint8_t {
  MainMenu,
  DrinkMenu,
  SizeMenu,
  Confirm,
  WaitingPayment,
  Processing,
  Complete,
  SoldOut,
  Status
};
enum class PopcornState : uint8_t {
  Idle,
  LoadingCorn,
  Popping
};
// --------------------------- DATA -----------------------------
struct Inventory {
  float popcornGrams = Config::POPCORN_INITIAL_G;
  float nachosGrams = Config::INITIAL_NACHOS_G;
  // Index order: Coca-Cola, Fanta, Sprite, Water.
  float drinkMl[4] = {
    Config::DRINK_TANK_ML,
    Config::DRINK_TANK_ML,
    Config::DRINK_TANK_ML,
    Config::DRINK_TANK_ML
  };
};
struct Order {
  Product product = Product::Popcorn;
  ServingSize size = ServingSize::Small;
  float price = 0.0f;
  bool paid = false;
  bool active = false;
};
Inventory inventory;
Order order;
UiState uiState = UiState::MainMenu;
PopcornState popcornState = PopcornState::Idle;
int mainIndex = 0;
int drinkIndex = 0;
int sizeIndex = 0;
unsigned long uiStateStartedAt = 0;
unsigned long lastScreenUpdate = 0;
unsigned long lastNavigation = 0;
unsigned long lastButtonChange = 0;
unsigned long popcornStateStartedAt = 0;
unsigned long dispenserStartedAt = 0;
unsigned long paymentStartedAt = 0;
bool dispenserActive = false;
bool previousButtonReading = HIGH;
bool stableButtonReading = HIGH;
char screenLine[Config::LCD_COLS + 1];
// --------------------------- TEXT -----------------------------
const char * productName(Product product) {
  switch (product) {
    case Product::Popcorn: return "Popcorn";
    case Product::Coke:    return "Coca-Cola";
    case Product::Fanta:   return "Fanta";
    case Product::Sprite:  return "Sprite";
    case Product::Water:   return "Water";
    case Product::Nachos:  return "Nachos";
  }
  return "Unknown";
}
const char * sizeName(ServingSize size) {
  switch (size) {
    case ServingSize::Small:  return "Small";
    case ServingSize::Medium: return "Medium";
    case ServingSize::Large:  return "Large";
  }
  return "Unknown";
}
uint8_t sizeNumber() {
  return static_cast<uint8_t>(order.size);
}
bool isDrink(Product product) {
  return product == Product::Coke ||
         product == Product::Fanta ||
         product == Product::Sprite ||
         product == Product::Water;
}
float calculatePrice(Product product, ServingSize size) {
  uint8_t i = static_cast<uint8_t>(size);
  if (product == Product::Popcorn) {
    return Config::POPCORN_PRICE[i];
  }
  if (product == Product::Nachos) {
    return Config::NACHOS_PRICE[i];
  }
  return Config::DRINK_PRICE[i];
}
// --------------------------- LCD ------------------------------
void printLine(uint8_t row, const char* text) {
  lcd.setCursor(0, row);
  uint8_t i = 0;
  while (text[i] != '\0' && i < Config::LCD_COLS) {
    lcd.print(text[i]);
    i++;
  }
  while (i < Config::LCD_COLS) {
    lcd.print(' ');
    i++;
  }
}
void printLineF(uint8_t row, const char * format, float value) {
  char buffer[Config::LCD_COLS + 1];
  snprintf(buffer, sizeof(buffer), format, value);
  printLine(row, buffer);
}
void printWelcome() {
  lcd.clear();
  printLine(0, " PUKANKOV MACHINE");
  printLine(1, "Professional Demo");
  printLine(2, "Initializing...");
  printLine(3, "Please wait");
}
// --------------------------- SOUND ----------------------------
void beep(uint16_t frequency = 1800, uint16_t duration = 80) {
  tone(Config::BUZZER, frequency, duration);
}
void soundSuccess() {
  tone(Config::BUZZER, 1900, 100);
}
void soundError() {
  tone(Config::BUZZER, 400, 350);
}
// --------------------------- RGB ------------------------------
void setRGB(bool red, bool green, bool blue) {
  digitalWrite(
    Config::LED_R,
    Config::COMMON_ANODE ? !red : red
  );
  digitalWrite(
    Config::LED_G,
    Config::COMMON_ANODE ? !green : green
  );
  digitalWrite(
    Config::LED_B,
    Config::COMMON_ANODE ? !blue : blue
  );
}
void updateStatusLED() {
  const bool blink = ((millis() / 350) % 2) == 0;
  switch (uiState) {
    case UiState::MainMenu:
    case UiState::DrinkMenu:
    case UiState::SizeMenu:
    case UiState::Confirm:
    case UiState::Status:
      setRGB(false, true, false);
      break;
    case UiState::WaitingPayment:
      setRGB(false, false, blink);
      break;
    case UiState::Processing:
      if (popcornState == PopcornState::Popping ||
          popcornState == PopcornState::LoadingCorn) {
        setRGB(true, true, false);
      } else {
        setRGB(false, true, true);
      }
      break;
    case UiState::Complete:
      setRGB(false, true, false);
      break;
    case UiState::SoldOut:
      setRGB(blink, false, false);
      break;
  }
}
// --------------------------- INPUT ----------------------------
bool pressed() {
  bool reading = digitalRead(Config::JOY_SW);
  if (reading != previousButtonReading) {
    previousButtonReading = reading;
    lastButtonChange = millis();
  }
  if (millis() - lastButtonChange >=
      Config::BUTTON_DEBOUNCE_MS) {
    if (reading != stableButtonReading) {
      stableButtonReading = reading;
      if (stableButtonReading == LOW) {
        return true;
      }
    }
  }
  return false;
}
// -1 = up, +1 = down, 0 = none
int8_t navigation() {
  static bool readyForMove = true;
  const int y = analogRead(Config::JOY_Y);
  // Require the stick to return to center before accepting another move.
  if (y >= 400 && y <= 600) {
    readyForMove = true;
    return 0;
  }
  if (!readyForMove) return 0;
  if (y < 350) {
    readyForMove = false;
    return -1;
  }
  if (y > 650) {
    readyForMove = false;
    return 1;
  }
  return 0;
}
bool leftPressed() {
  if (analogRead(Config::JOY_X) >= 180) {
    return false;
  }
  if (millis() - lastNavigation < Config::NAV_REPEAT_MS) {
    return false;
  }
  lastNavigation = millis();
  return true;
}
int wrapIndex(int index, int count) {
  if (index < 0) return count - 1;
  if (index >= count) return 0;
  return index;
}
// --------------------------- PUMPS ----------------------------
AccelStepper * selectedPump() {
  switch (order.product) {
    case Product::Coke:  return &pumpCoke;
    case Product::Fanta: return &pumpFanta;
    case Product::Sprite:return &pumpSprite;
    case Product::Water: return &pumpWater;
    default: return nullptr;
  }
}
void stopPumps() {
  pumpCoke.setSpeed(0);
  pumpFanta.setSpeed(0);
  pumpSprite.setSpeed(0);
  pumpWater.setSpeed(0);
}
void runPumpService() {
  // Всички помпи са независими.
  // При тази версия се активира само избраната помпа.
  if (uiState != UiState::Processing ||
      !isDrink(order.product)) {
    return;
  }
  AccelStepper * pump = selectedPump();
  if (pump != nullptr && dispenserActive) {
    pump->runSpeed();
  }
}
// --------------------------- RFID -----------------------------
bool scanCard() {
  if (!rfid.PICC_IsNewCardPresent()) {
    return false;
  }
  if (!rfid.PICC_ReadCardSerial()) {
    return false;
  }
  Serial.print(F("[RFID] UID: "));
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) {
      Serial.print('0');
    }
    Serial.print(rfid.uid.uidByte[i], HEX);
    if (i + 1 < rfid.uid.size) {
      Serial.print(':');
    }
  }
  Serial.println();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return true;
}
// --------------------------- INVENTORY ------------------------
float popcornRequired() {
  return Config::POPCORN_SERVING_G[sizeNumber()];
}
float nachosRequired() {
  return Config::NACHOS_SERVING_G[sizeNumber()];
}
bool popcornAvailable() {
  return inventory.popcornGrams >= popcornRequired();
}
bool nachosAvailable() {
  return inventory.nachosGrams >= nachosRequired();
}
void subtractPopcornStock() {
  inventory.popcornGrams -= popcornRequired();
  if (inventory.popcornGrams < 0.0f) inventory.popcornGrams = 0.0f;
}
void subtractNachosStock() {
  inventory.nachosGrams -= nachosRequired();
  if (inventory.nachosGrams < 0.0f) {
    inventory.nachosGrams = 0.0f;
  }
}
uint8_t drinkIndexFor(Product product) {
  switch (product) {
    case Product::Coke: return 0;
    case Product::Fanta: return 1;
    case Product::Sprite: return 2;
    case Product::Water: return 3;
    default: return 255;
  }
}
float drinkRequiredMl() {
  return static_cast<float>(Config::DRINK_SERVING_ML[sizeNumber()]);
}
bool drinkAvailable() {
  uint8_t index = drinkIndexFor(order.product);
  return index < 4 && inventory.drinkMl[index] >= drinkRequiredMl();
}
void subtractDrinkStock() {
  uint8_t index = drinkIndexFor(order.product);
  if (index < 4) {
    inventory.drinkMl[index] -= drinkRequiredMl();
    if (inventory.drinkMl[index] < 0.0f) inventory.drinkMl[index] = 0.0f;
  }
}
// --------------------------- STATE MANAGEMENT -----------------
void setUiState(UiState next) {
  uiState = next;
  uiStateStartedAt = millis();
  lastScreenUpdate = 0;
}
void setPopcornState(PopcornState next) {
  popcornState = next;
  popcornStateStartedAt = millis();
  if (next == PopcornState::LoadingCorn) {
    servoCorn.write(Config::CORN_OPEN);
    Serial.println(F("[POPCORN] Loading corn"));
  }
}
void returnToMenu() {
  order.active = false;
  order.paid = false;
  dispenserActive = false;
  stopPumps();
  servoCorn.write(Config::CORN_CLOSED);
  if (popcornState != PopcornState::Popping &&
      popcornState != PopcornState::LoadingCorn) {
    servoMachine.write(Config::MACHINE_OFF);
  }
  servoPopcorn.write(Config::DISPENSER_CLOSED);
  servoNachos.write(Config::DISPENSER_CLOSED);
  setUiState(UiState::MainMenu);
}
// --------------------------- ORDER FLOW -----------------------
void selectProduct(Product product) {
  order.product = product;
  order.size = ServingSize::Small;
  order.price = calculatePrice(product, order.size);
  order.active = true;
  order.paid = false;
  sizeIndex = 0;
  setUiState(UiState::SizeMenu);
}
void refreshPrice() {
  order.size = static_cast<ServingSize>(sizeIndex);
  order.price = calculatePrice(order.product, order.size);
}
void cancelOrder() {
  order.active = false;
  order.paid = false;
  setUiState(UiState::MainMenu);
}
void beginPayment() {
  refreshPrice();
  if ((order.product == Product::Nachos && !nachosAvailable()) ||
      (isDrink(order.product) && !drinkAvailable())) {
    soundError();
    setUiState(UiState::SoldOut);
    return;
  }
  order.price = calculatePrice(order.product, order.size);
  paymentStartedAt = millis();
  setUiState(UiState::WaitingPayment);
}
void acceptSimulatedPayment() {
  order.paid = true;
  Serial.print(F("[ORDER] Payment simulated: "));
  Serial.print(order.price, 2);
  Serial.println(F(" EUR"));
  soundSuccess();
  setUiState(UiState::Processing);
  if (order.product == Product::Popcorn) {
    if (popcornAvailable()) {
      dispenserStartedAt = millis();
      dispenserActive = false;
    } else {
      // Производството се стартира в popcornService().
      setPopcornState(PopcornState::LoadingCorn);
    }
  } else {
    dispenserStartedAt = millis();
    dispenserActive = false;
  }
}
// --------------------------- POPCORN SERVICE ------------------
void popcornService() {
  // Автоматично производство във фонов режим — не зависи от поръчка.
  // Започва нова партида, когато наличността падне под 5 kg.
  switch (popcornState) {
    case PopcornState::Idle:
      // Ако има достатъчно готови пуканки, няма
      // нужда от нова партида.
      if (inventory.popcornGrams < Config::POPCORN_REORDER_BELOW_G) {
        setPopcornState(PopcornState::LoadingCorn);
      }
      break;
    case PopcornState::LoadingCorn:
      if (millis() - popcornStateStartedAt >=
          Config::CORN_LOADING_MS) {
        servoCorn.write(Config::CORN_CLOSED);
        servoMachine.write(Config::MACHINE_ON);
        Serial.println(F("[POPCORN] Machine ON"));
        setPopcornState(PopcornState::Popping);
      }
      break;
    case PopcornState::Popping: {
      unsigned long elapsed =
        millis() - popcornStateStartedAt;
      if (elapsed >= Config::POPPING_MS) {
        servoMachine.write(Config::MACHINE_OFF);
        inventory.popcornGrams += Config::POPCORN_BATCH_G;
        if (inventory.popcornGrams > Config::POPCORN_MAX_G) {
          inventory.popcornGrams = Config::POPCORN_MAX_G;
        }
        Serial.print(F("[POPCORN] Batch ready. Stock: "));
        Serial.print(inventory.popcornGrams / 1000.0f, 1);
        Serial.println(F(" kg"));
        setPopcornState(PopcornState::Idle);
        dispenserStartedAt = millis();
        dispenserActive = false;
      }
      break;
    }
  }
}
// --------------------------- DISPENSING ------------------------
void beginDispenserIfNeeded() {
  if (dispenserActive) {
    return;
  }
  dispenserActive = true;
  dispenserStartedAt = millis();
  switch (order.product) {
    case Product::Popcorn:
      servoPopcorn.write(Config::DISPENSER_OPEN);
      break;
    case Product::Nachos:
      servoNachos.write(Config::DISPENSER_OPEN);
      break;
    default: {
      AccelStepper * pump = selectedPump();
      if (pump != nullptr) {
        pump->setSpeed(Config::PUMP_SPEED);
      }
      break;
    }
  }
}
void finishOrder() {
  dispenserActive = false;
  stopPumps();
  servoPopcorn.write(Config::DISPENSER_CLOSED);
  servoNachos.write(Config::DISPENSER_CLOSED);
  servoCorn.write(Config::CORN_CLOSED);
  if (popcornState != PopcornState::Popping &&
      popcornState != PopcornState::LoadingCorn) {
    servoMachine.write(Config::MACHINE_OFF);
  }
  if (order.product == Product::Popcorn) {
    subtractPopcornStock();
  } else if (order.product == Product::Nachos) {
    subtractNachosStock();
  } else if (isDrink(order.product)) {
    subtractDrinkStock();
  }
  Serial.print(F("[ORDER] Complete: "));
  Serial.print(productName(order.product));
  Serial.print(F(" / "));
  Serial.println(sizeName(order.size));
  if (isDrink(order.product)) {
    uint8_t drinkIdx = drinkIndexFor(order.product);
    if (drinkIdx < 4) {
      Serial.print(F("[INVENTORY] "));
      Serial.print(productName(order.product));
      Serial.print(F(" remaining: "));
      Serial.print(inventory.drinkMl[drinkIdx] / 1000.0f, 2);
      Serial.println(F(" L"));
    }
  }
  tone(Config::BUZZER, 1900, 100);
  setUiState(UiState::Complete);
}
void dispensingService() {
  if (uiState != UiState::Processing) {
    return;
  }
  // Производството върви отделно във фонов режим.
  // Поръчката се обслужва веднага, ако има достатъчно готови пуканки.
  if (order.product == Product::Popcorn && !popcornAvailable()) {
    return;
  }
  beginDispenserIfNeeded();
  unsigned long duration = 0;
  switch (order.product) {
    case Product::Popcorn:
      duration = Config::POPCORN_TIME_MS[sizeNumber()];
      break;
    case Product::Nachos:
      duration = Config::NACHOS_TIME_MS[sizeNumber()];
      break;
    case Product::Coke:
    case Product::Fanta:
    case Product::Sprite:
    case Product::Water:
      duration = Config::DRINK_TIME_MS[sizeNumber()];
      break;
  }
  // Помпата се обслужва непрекъснато в loop().
  if (isDrink(order.product)) {
    AccelStepper * pump = selectedPump();
    if (pump != nullptr) {
      pump->runSpeed();
    }
  }
  if (millis() - dispenserStartedAt >= duration) {
    finishOrder();
  }
}
// --------------------------- UI: MAIN MENU --------------------
void handleMainMenu() {
  int8_t nav = navigation();
  if (nav != 0) {
    mainIndex = wrapIndex(mainIndex + nav, 4);
    beep();
    lastScreenUpdate = 0;
  }
  if (!pressed()) {
    return;
  }
  beep();
  switch (mainIndex) {
    case 0:
      selectProduct(Product::Popcorn);
      break;
    case 1:
      drinkIndex = 0;
      setUiState(UiState::DrinkMenu);
      break;
    case 2:
      selectProduct(Product::Nachos);
      break;
    case 3:
      setUiState(UiState::Status);
      break;
  }
}
void handleDrinkMenu() {
  int8_t nav = navigation();
  if (nav != 0) {
    drinkIndex = wrapIndex(drinkIndex + nav, 4);
    beep();
    lastScreenUpdate = 0;
  }
  if (leftPressed()) {
    setUiState(UiState::MainMenu);
    return;
  }
  if (!pressed()) {
    return;
  }
  switch (drinkIndex) {
    case 0: selectProduct(Product::Coke); break;
    case 1: selectProduct(Product::Fanta); break;
    case 2: selectProduct(Product::Sprite); break;
    case 3: selectProduct(Product::Water); break;
  }
  beep();
}
void handleSizeMenu() {
  int8_t nav = navigation();
  if (nav != 0) {
    sizeIndex = wrapIndex(sizeIndex + nav, 3);
    refreshPrice();
    beep();
    lastScreenUpdate = 0;
  }
  if (leftPressed()) {
    if (isDrink(order.product)) {
      setUiState(UiState::DrinkMenu);
    } else {
      setUiState(UiState::MainMenu);
    }
    return;
  }
  if (pressed()) {
    refreshPrice();
    beep();
    setUiState(UiState::Confirm);
  }
}
void handleConfirm() {
  if (leftPressed()) {
    setUiState(UiState::SizeMenu);
    return;
  }
  if (pressed()) {
    beginPayment();
    beep();
  }
}
void handlePayment() {
  if (leftPressed()) {
    cancelOrder();
    return;
  }
  if (millis() - paymentStartedAt >=
      Config::PAYMENT_TIMEOUT_MS) {
    Serial.println(F("[PAYMENT] Timed out"));
    soundError();
    cancelOrder();
    return;
  }
  if (scanCard()) {
    acceptSimulatedPayment();
  }
}
// --------------------------- DISPLAY RENDERER -----------------
void renderMainMenu() {
  printLine(0, " PUKANKOV MACHINE");
  const char * items[4] = {
    "POPCORN",
    "DRINKS",
    "NACHOS",
    "STATUS"
  };
  // Показваме максимум 3 опции под заглавието.
  int start = mainIndex - 2;
  if (start < 0) start = 0;
  if (start > 1) start = 1;
  for (int row = 0; row < 3; row++) {
    int item = start + row;
    char buffer[Config::LCD_COLS + 1];
    snprintf(
      buffer,
      sizeof(buffer),
      "%s%s",
      item == mainIndex ? "> " : "  ",
      items[item]
    );
    printLine(row + 1, buffer);
  }
}
void renderDrinkMenu() {
  const char * items[4] = {
    "Coca-Cola",
    "Fanta",
    "Sprite",
    "Water"
  };
  printLine(0, "SELECT DRINK");
  int start = drinkIndex - 2;
  if (start < 0) start = 0;
  if (start > 1) start = 1;
  for (int row = 0; row < 3; row++) {
    int item = start + row;
    char buffer[Config::LCD_COLS + 1];
    snprintf(
      buffer,
      sizeof(buffer),
      "%s%s",
      item == drinkIndex ? "> " : "  ",
      items[item]
    );
    printLine(row + 1, buffer);
  }
}
void renderSizeMenu() {
  printLine(0, productName(order.product));
  const char * labels[3] = {
    "Small",
    "Medium",
    "Large"
  };
  for (int i = 0; i < 3; i++) {
    char buffer[Config::LCD_COLS + 1];
    snprintf(
      buffer,
      sizeof(buffer),
      "%s%s",
      i == sizeIndex ? "> " : "  ",
      labels[i]
    );
    printLine(i + 1, buffer);
  }
}
void renderConfirm() {
  char buffer[Config::LCD_COLS + 1];
  char priceText[12];
  dtostrf(order.price, 5, 2, priceText);
  printLine(0, "CONFIRM ORDER");
  snprintf(buffer, sizeof(buffer), "%s %s",
           productName(order.product), sizeName(order.size));
  printLine(1, buffer);
  snprintf(buffer, sizeof(buffer), "Price: %s EUR", priceText);
  printLine(2, buffer);
  printLine(3, "Press to continue");
}
void renderPayment() {
  char buffer[Config::LCD_COLS + 1];
  char priceText[12];
  dtostrf(order.price, 5, 2, priceText);
  printLine(0, "WAITING FOR PAYMENT");
  printLine(1, productName(order.product));
  snprintf(buffer, sizeof(buffer), "%s EUR", priceText);
  printLine(2, buffer);
  printLine(3, "Tap RFID / Left=Back");
}
void renderProcessing() {
  if (order.product == Product::Popcorn &&
      !popcornAvailable() &&
      popcornState != PopcornState::Idle) {
    printLine(0, "POPCORN PRODUCTION");
    if (popcornState == PopcornState::LoadingCorn) {
      printLine(1, "Loading corn...");
      printLine(2, "Preparing batch");
    } else {
      unsigned long elapsed =
        millis() - popcornStateStartedAt;
      unsigned long remaining = 0;
      if (elapsed < Config::POPPING_MS) {
        remaining = (Config::POPPING_MS - elapsed) / 1000;
      }
      char buffer[Config::LCD_COLS + 1];
      printLine(1, "Machine is working");
      snprintf(
        buffer,
        sizeof(buffer),
        "Time left: %lu sec",
        remaining
      );
      printLine(2, buffer);
    }
    printLine(3, "Please wait...");
    return;
  }
  printLine(0, "ORDER IN PROGRESS");
  printLine(1, productName(order.product));
  printLine(2, sizeName(order.size));
  printLine(3, "Please wait...");
}
void renderStatus() {
  char buffer[Config::LCD_COLS + 1];
  char popcornText[12];
  char nachosText[12];
  dtostrf(inventory.popcornGrams / 1000.0f, 4, 1, popcornText);
  dtostrf(inventory.nachosGrams / 1000.0f, 4, 1, nachosText);
  printLine(0, "MACHINE INVENTORY");
  snprintf(buffer, sizeof(buffer), "Popcorn: %s kg", popcornText);
  printLine(1, buffer);
  snprintf(buffer, sizeof(buffer), "Nachos: %s kg", nachosText);
  printLine(2, buffer);
  printLine(3, "4 drink tanks: 500L");
}
void renderDisplay() {
  if (millis() - lastScreenUpdate <
      Config::SCREEN_REFRESH_MS) {
    return;
  }
  lastScreenUpdate = millis();
  switch (uiState) {
    case UiState::MainMenu:
      renderMainMenu();
      break;
    case UiState::DrinkMenu:
      renderDrinkMenu();
      break;
    case UiState::SizeMenu:
      renderSizeMenu();
      break;
    case UiState::Confirm:
      renderConfirm();
      break;
    case UiState::WaitingPayment:
      renderPayment();
      break;
    case UiState::Processing:
      renderProcessing();
      break;
    case UiState::Complete:
      printLine(0, "ORDER COMPLETE!");
      printLine(1, productName(order.product));
      printLine(2, sizeName(order.size));
      printLine(3, "Thank you!");
      break;
    case UiState::SoldOut:
      printLine(0, "PRODUCT UNAVAILABLE");
      printLine(1, productName(order.product));
      printLine(2, "Please choose again");
      printLine(3, "Returning to menu...");
      break;
    case UiState::Status:
      renderStatus();
      break;
  }
}
// --------------------------- SETUP ----------------------------
void setup() {
  Serial.begin(115200);
  Wire.begin();
  lcd.init();
  lcd.backlight();
  pinMode(Config::JOY_SW, INPUT_PULLUP);
  pinMode(Config::BUZZER, OUTPUT);
  pinMode(Config::LED_R, OUTPUT);
  pinMode(Config::LED_G, OUTPUT);
  pinMode(Config::LED_B, OUTPUT);
  servoCorn.attach(Config::SERVO_CORN);
  servoMachine.attach(Config::SERVO_MACHINE);
  servoPopcorn.attach(Config::SERVO_POPCORN);
  servoNachos.attach(Config::SERVO_NACHOS);
  servoCorn.write(Config::CORN_CLOSED);
  servoMachine.write(Config::MACHINE_OFF);
  servoPopcorn.write(Config::DISPENSER_CLOSED);
  servoNachos.write(Config::DISPENSER_CLOSED);
  pumpCoke.setMaxSpeed(800);
  pumpFanta.setMaxSpeed(800);
  pumpSprite.setMaxSpeed(800);
  pumpWater.setMaxSpeed(800);
  stopPumps();
  SPI.begin();
  // На Mega D53 трябва да остане OUTPUT за SPI master.
  pinMode(Config::RFID_SS, OUTPUT);
  digitalWrite(Config::RFID_SS, HIGH);
  rfid.PCD_Init();
  printWelcome();
  setRGB(false, false, false);
  Serial.println(F("--------------------------------"));
  Serial.println(F("PUKANKOV MACHINE v2.0"));
  Serial.println(F("Arduino Mega 2560"));
  Serial.println(F("RFID payment: simulation only"));
  Serial.println(F("--------------------------------"));
  beep(1800, 100);
  delay(700);
  setUiState(UiState::MainMenu);
}
// --------------------------- MAIN LOOP ------------------------
void loop() {
  updateStatusLED();
  // Моторите трябва да се обслужват често.
  runPumpService();
  // Автоматично поддържане на запас от пуканки, независимо от поръчките.
  popcornService();
  // Показваме текущото състояние.
  renderDisplay();
  switch (uiState) {
    case UiState::MainMenu:
      handleMainMenu();
      break;
    case UiState::DrinkMenu:
      handleDrinkMenu();
      break;
    case UiState::SizeMenu:
      handleSizeMenu();
      break;
    case UiState::Confirm:
      handleConfirm();
      break;
    case UiState::WaitingPayment:
      handlePayment();
      break;
    case UiState::Processing:
      dispensingService();
      break;
    case UiState::Complete:
      if (millis() - uiStateStartedAt >= 3000) {
        returnToMenu();
      }
      break;
    case UiState::SoldOut:
      if (millis() - uiStateStartedAt >= 2500) {
        returnToMenu();
      }
      break;
    case UiState::Status:
      if (pressed() || leftPressed()) {
        setUiState(UiState::MainMenu);
      }
      break;
  }
}
