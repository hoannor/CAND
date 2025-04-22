#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9 // Chân RST của MFRC522
#define SS_PIN 10 // Chân SDA của MFRC522

MFRC522 rfid(SS_PIN, RST_PIN); // Khởi tạo đối tượng MFRC522

void setup()
{
    Serial.begin(9600); // Khởi tạo giao tiếp Serial với tốc độ 9600 baud
    SPI.begin();        // Khởi tạo giao tiếp SPI
    rfid.PCD_Init();    // Khởi tạo module MFRC522
    Serial.println("Arduino ready. Waiting for RFID card...");
}

void loop()
{
    // Kiểm tra xem có thẻ RFID nào được quét không
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial())
    {
        // Đọc mã UID của thẻ
        String rfidCode = "";
        for (byte i = 0; i < rfid.uid.size; i++)
        {
            // Đảm bảo mỗi byte được biểu diễn bằng 2 ký tự hex (thêm số 0 nếu cần)
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
}