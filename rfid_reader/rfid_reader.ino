#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>

#define RST_PIN 9         // Chân RST của MFRC522
#define SS_PIN 10         // Chân SDA của MFRC522
#define SERVO_PIN 5       // Chân điều khiển servo
#define IR_PIN 6          // Chân cảm biến hồng ngoại
#define SERVO_OPEN_POS 90 // Góc servo khi mở cổng (độ)
#define SERVO_CLOSE_POS 0 // Góc servo khi đóng cổng (độ)

MFRC522 rfid(SS_PIN, RST_PIN);  // Khởi tạo đối tượng MFRC522
Servo gateServo;                // Khởi tạo đối tượng Servo
bool gateOpen = false;          // Trạng thái cổng
unsigned long gateOpenTime = 0; // Thời điểm mở cổng
bool waitingForIR = false;      // Đang chờ tín hiệu IR

void setup()
{
    Serial.begin(9600); // Khởi tạo giao tiếp Serial với tốc độ 9600 baud
    SPI.begin();        // Khởi tạo giao tiếp SPI
    rfid.PCD_Init();    // Khởi tạo module MFRC522

    // Khởi tạo Servo
    gateServo.attach(SERVO_PIN);
    gateServo.write(SERVO_CLOSE_POS); // Đặt servo về vị trí đóng ban đầu
    gateOpen = false;

    // Khởi tạo cảm biến hồng ngoại
    pinMode(IR_PIN, INPUT);

    Serial.println("Arduino ready. Waiting for RFID card...");
}

void loop()
{
    // Kiểm tra lệnh từ Serial (từ client)
    if (Serial.available() > 0)
    {
        String command = Serial.readStringUntil('\n');
        command.trim();
        Serial.print("Received command: ");
        Serial.println(command);

        if (command == "OPEN_GATE")
        {
            openGate();
        }
    }

    // Kiểm tra thẻ RFID
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial())
    {
        // Đọc mã UID của thẻ
        String rfidCode = "";
        for (byte i = 0; i < rfid.uid.size; i++)
        {
            if (rfid.uid.uidByte[i] < 0x10)
            {
                rfidCode += "0"; // Thêm số 0 nếu giá trị nhỏ hơn 16
            }
            rfidCode += String(rfid.uid.uidByte[i], HEX);
        }
        rfidCode.toUpperCase();

        // Gửi mã RFID qua Serial
        Serial.print("RFID:");
        Serial.println(rfidCode);

        // Log chi tiết để gỡ lỗi
        Serial.print("UID size: ");
        Serial.println(rfid.uid.size);
        Serial.print("Raw UID: ");
        for (byte i = 0; i < rfid.uid.size; i++)
        {
            Serial.print(rfid.uid.uidByte[i], HEX);
            Serial.print(" ");
        }
        Serial.println();

        // Dừng giao tiếp với thẻ hiện tại
        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();

        // Chờ một chút trước khi quét thẻ tiếp theo
        delay(1000);
    }

    // Xử lý cảm biến hồng ngoại khi cổng đang mở
    if (gateOpen && waitingForIR)
    {
        int irState = digitalRead(IR_PIN);
        Serial.print("IR Sensor State: ");
        Serial.println(irState);

        if (irState == LOW)
        { // Cảm biến IR phát hiện tín hiệu (giả sử LOW khi có vật cản)
            Serial.println("IR sensor triggered. Starting 10-second delay...");
            waitingForIR = false;    // Dừng chờ tín hiệu IR
            gateOpenTime = millis(); // Ghi lại thời điểm cảm biến kích hoạt
        }
    }

    // Đóng cổng sau 10 giây kể từ khi cảm biến IR kích hoạt
    if (gateOpen && !waitingForIR && (millis() - gateOpenTime >= 10000))
    {
        closeGate();
    }
}

void openGate()
{
    Serial.println("Opening gate...");
    gateServo.write(SERVO_OPEN_POS); // Mở cổng
    gateOpen = true;
    waitingForIR = true; // Bắt đầu chờ tín hiệu từ cảm biến IR
}

void closeGate()
{
    Serial.println("Closing gate...");
    gateServo.write(SERVO_CLOSE_POS); // Đóng cổng
    gateOpen = false;
    waitingForIR = false;
}