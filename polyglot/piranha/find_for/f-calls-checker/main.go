package main

import (
	"bufio"
	"log"
	"os"
	"path/filepath"
	"strings"
)

const (
	callToLookFor = ".GetBoolValue("
)

func main() {
	f, err := os.OpenFile("paths.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
	}

	fNoImport, err := os.OpenFile("paths_no_import.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
	}

	fTest, _ := os.OpenFile("paths_test.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	fTestNoImport, _ := os.OpenFile("paths_test_no_import.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)

	defer f.Close()
	defer fNoImport.Close()
	defer fTest.Close()
	defer fTestNoImport.Close()

	rootPath := "/home/user/go-code/src/"
	filepath.Walk(rootPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			log.Fatal(err)
		}

		if info.IsDir() {
			return nil
		}
		ext := filepath.Ext(path)
		if ext == ".go" {
			if hasCall(path) {
				if hasImport(path) {
					if strings.HasSuffix(path, "_test.go") {
						fTest.WriteString(path + "\n")
					} else {
						if _, err = f.WriteString(path + "\n"); err != nil {
							log.Fatal(err)
						}
					}
				} else {
					if strings.HasSuffix(path, "_test.go") {
						fTestNoImport.WriteString(path + "\n")
					} else {
						if _, err = fNoImport.WriteString(path + "\n"); err != nil {
							log.Fatal(err)
						}
					}
				}
			}
		}
		return nil
	})
}

func hasImport(path string) bool {
	file, err := os.Open(path)
	if err != nil {
		log.Fatal("Could not open the file: ", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	foundImport := false
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "import (") {
			foundImport = true
		}
		if strings.Contains(line, "\""+os.Args[1]+"\"") {
			return true
		}
		if foundImport && line == ")" {
			break
		}
	}

	return false
}

func hasCall(path string) bool {
	file, err := os.ReadFile(path)
	if err != nil {
		log.Fatal("Could not read the file", err)
	}

	return strings.Contains(string(file), callToLookFor)
}
