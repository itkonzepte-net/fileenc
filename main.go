package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
)

// encrypt encrypts the file at the given path using AES and saves it with the .enc extension
func encrypt(filePath string, key []byte) error {
	// Open the source file
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	// Create the destination file with .enc extension
	encFilePath := filePath + ".enc"
	encFile, err := os.Create(encFilePath)
	if err != nil {
		return fmt.Errorf("failed to create encrypted file: %w", err)
	}
	defer encFile.Close()

	// Generate a random IV
	block, err := aes.NewCipher(key)
	if err != nil {
		return fmt.Errorf("failed to create cipher: %w", err)
	}
	iv := make([]byte, aes.BlockSize)
	if _, err := io.ReadFull(rand.Reader, iv); err != nil {
		return fmt.Errorf("failed to generate IV: %w", err)
	}

	// Write the IV to the encrypted file
	if _, err := encFile.Write(iv); err != nil {
		return fmt.Errorf("failed to write IV to file: %w", err)
	}

	// Create a cipher stream and encrypt the file
	stream := cipher.NewCFBEncrypter(block, iv)
	writer := &cipher.StreamWriter{S: stream, W: encFile}
	if _, err := io.Copy(writer, file); err != nil {
		return fmt.Errorf("failed to encrypt file: %w", err)
	}

	return nil
}

// decrypt decrypts the .enc file at the given path using AES and removes the .enc extension
func decrypt(filePath string, key []byte) error {
	// Ensure the file has the .enc extension
	if !strings.HasSuffix(filePath, ".enc") {
		return errors.New("file does not have .enc extension")
	}

	// Open the encrypted file
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open encrypted file: %w", err)
	}
	defer file.Close()

	// Create the destination file without the .enc extension
	decFilePath := strings.TrimSuffix(filePath, ".enc")
	decFile, err := os.Create(decFilePath)
	if err != nil {
		return fmt.Errorf("failed to create decrypted file: %w", err)
	}
	defer decFile.Close()

	// Read the IV from the encrypted file
	block, err := aes.NewCipher(key)
	if err != nil {
		return fmt.Errorf("failed to create cipher: %w", err)
	}
	iv := make([]byte, aes.BlockSize)
	if _, err := io.ReadFull(file, iv); err != nil {
		return fmt.Errorf("failed to read IV from file: %w", err)
	}

	// Create a cipher stream and decrypt the file
	stream := cipher.NewCFBDecrypter(block, iv)
	reader := &cipher.StreamReader{S: stream, R: file}
	if _, err := io.Copy(decFile, reader); err != nil {
		return fmt.Errorf("failed to decrypt file: %w", err)
	}

	return nil
}

func main() {
	pass := flag.String("key", "", "password for encryption")
	sourceFile := flag.String("source", "", "file subject for processing, no .enc extension!")
	decryptFlag := flag.Bool("decrypt", false, "run decryption, default encryption")
	flag.Parse()

	if len(*pass) == 0 {
		fmt.Printf("no key present, use -key flag\n")
		return
	}

	// Example usage
	key := []byte(*pass) // 16 bytes for AES-128

	if len(key) != 16 && len(key) != 24 && len(key) != 32 {
		fmt.Printf("Key must be 16, 24, or 32 bytes long, got %d.\n", len(key))
		return
	}

	if !*decryptFlag {
		// Encrypt the file
		if err := encrypt(*sourceFile, key); err != nil {
			fmt.Printf("Error encrypting file: %v\n", err)
			return
		}
		fmt.Println("File encrypted successfully.")

	} else {
		// Decrypt the file
		if err := decrypt(*sourceFile+".enc", key); err != nil {
			fmt.Printf("Error decrypting file: %v\n", err)
			return
		}
		fmt.Println("File decrypted successfully.")
	}
}
