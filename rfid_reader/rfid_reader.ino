// Дмитрий Осипов. http://www.youtube.com/user/d36073?feature=watch

#include <SPI.h>
#include <MFRC522.h> // thu vien "RFID".
const int LED1 = 2;  // LED đỏ
const int LED2 = 3;  // LED xanh
/*
Ket noi voi Arduino Uno hoac Mega
 ----------------------------------------------------- Nicola Coppola
 * Pin layout should be as follows:
 * Signal     Pin              Pin               Pin
 *            Arduino Uno      Arduino Mega      MFRC522 board
 * ------------------------------------------------------------
 * Reset      9                5                 RST
 * SPI SS     10               53                SDA
 * SPI MOSI   11               51                MOSI
 * SPI MISO   12               50                MISO
 * SPI SCK    13               52                SCK

 */

#define SS_PIN 10
#define RST_PIN 9

MFRC522 mfrc522(SS_PIN, RST_PIN);
unsigned long uidDec, uidDecTemp; // hien thi so UID dang thap phan
byte bCounter, readBit;
unsigned long ticketNumber;

// Khai báo UID của thẻ hợp lệ (thay bằng UID của thẻ của bạn)
String validCard = ""; // Điền UID thẻ của bạn vào đây

void setup()
{
    pinMode(LED1, OUTPUT);
    pinMode(LED2, OUTPUT);
    digitalWrite(LED1, LOW); // Tắt LED đỏ
    digitalWrite(LED2, LOW); // Tắt LED xanh
    Serial.begin(9600);
    SPI.begin();
    mfrc522.PCD_Init();
    Serial.println("Đang chờ thẻ...");
}

void loop()
{
    // Kiểm tra nếu có thẻ mới
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial())
    {
        Serial.println("Đã phát hiện thẻ!");

        // Đọc và hiển thị UID
        String content = "";
        Serial.print("UID của thẻ: ");
        for (byte i = 0; i < mfrc522.uid.size; i++)
        {
            Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " ");
            Serial.print(mfrc522.uid.uidByte[i], HEX);
            content.concat(String(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " "));
            content.concat(String(mfrc522.uid.uidByte[i], HEX));
        }
        Serial.println();
        content.toUpperCase();

        // Nếu đây là lần đầu đọc thẻ, lưu lại UID
        if (validCard.length() == 0)
        {
            validCard = content;
            Serial.println("Đã lưu thẻ này làm thẻ hợp lệ!");
            digitalWrite(LED2, HIGH); // Bật LED xanh
            delay(1000);
            digitalWrite(LED2, LOW); // Tắt LED xanh
        }
        // Kiểm tra thẻ
        else if (content.substring(1) == validCard.substring(1))
        {
            Serial.println("Thẻ hợp lệ - Truy cập được chấp nhận");
            digitalWrite(LED2, HIGH); // Bật LED xanh
            delay(1000);
            digitalWrite(LED2, LOW); // Tắt LED xanh
        }
        else
        {
            Serial.println("Thẻ không hợp lệ - Truy cập bị từ chối");
            digitalWrite(LED1, HIGH); // Bật LED đỏ
            delay(1000);
            digitalWrite(LED1, LOW); // Tắt LED đỏ
        }

        // Dừng đọc thẻ hiện tại
        mfrc522.PICC_HaltA();
        delay(1000);
    }
}

void printIssueDate(unsigned int incoming)
{

    boolean isLeap = true; // kiem tra nam nhuan
    int days[] = {
        // cac ngay cuoi cung trong thang theo thu tu doi voi nam binh thuong
        0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
    byte dayOfMonth, monthCounter;
    unsigned int yearCount;

    // bat dau tinh tu 01.01.1992
    //  incoming = incoming+1;

    // tinh nam, so ngay ke tu khi san xuat
    for (yearCount = 1992; incoming > 366; yearCount++)
    {

        if ((yearCount % 4 == 0 && yearCount % 100 != 0) || yearCount % 400 == 0)
        {
            incoming = incoming - 366;
            isLeap = true;
        }
        else
        {
            incoming = incoming - 365;
            isLeap = false;
        }
    }
    // tinh so thu tu thang
    for (monthCounter = 0; incoming > days[monthCounter]; monthCounter++)
    {
    }

    // tinh so thu tu ngay trong thang

    if (isLeap == true)
    { // neu nam nhuan

        // neu khong phai thang dau tien, thi them 1 vao ngay cuoi cung cua thang
        if (days[monthCounter - 1] > 31)
        {
            dayOfMonth = incoming - (days[monthCounter - 1] + 1);
        }
        else
        {
            dayOfMonth = incoming - (days[monthCounter - 1]);
        }
    }
    // neu la thang dau tien
    else
    {
        dayOfMonth = incoming - (days[monthCounter - 1]); // neu khong phai nam nhuan
    }
    Serial.print("            [");
    Serial.print(dayOfMonth);
    Serial.print(".");
    Serial.print(monthCounter);
    Serial.print(".");
    Serial.print(yearCount);
    Serial.println("]");
}

void setBitsForGood(byte daBeat)
{
    if (daBeat == 1)
    {
        bitSet(ticketNumber, bCounter);
        bCounter = bCounter + 1;
    }
    else
    {
        bitClear(ticketNumber, bCounter);
        bCounter = bCounter + 1;
    }
}