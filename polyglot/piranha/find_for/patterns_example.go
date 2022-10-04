package main

import (
	"fmt"
	"time"
)

func f(from string) {
	for i := 0; i < 3; i++ {
		fmt.Println(from, ":", i)
	}
}

func main() {

	f("direct")

	go f("goroutine")

	go func(msg string) {
		fmt.Println(msg)
	}("going")

	time.Sleep(time.Second)
	fmt.Println("done")
}

func go_stmt() {
	for i := 0; i < 10; i++ {
		go f(i) // go_statement gets matched
	}
	var input string
	fmt.Scanln(&input)
}

func go_after() {
	for i := 0; i < 10; i++ {
		go f(i) // go_statement gets matched
		fmt.Println("only after")
	}
}

func go_before() {
	for i := 0; i < 10; i++ {
		fmt.Println("only before")
		go f(i) // go_statement gets matched
	}
}

func go_stmt3() {
	for i := 0; i < 10; i++ {
		fmt.Println("Before")
		go f(i) // go_statement gets matched
		fmt.Println("wololo")
	}
}

func f3() {
	var pow = []int{1, 2, 4, 8, 16, 32, 64, 128}
	for i, v := range pow {
		go fmt.Printf("2**%d = %d\n", i, v)
	}
}

func f5() {
	for i := 0; i < 10; i++ {
		x := i
		y := x + 1
		go fmt.Sprintf("%v %v", x, y)
	}
}

func f5_after() {
	for i := 0; i < 10; i++ {
		x := i
		y := x + 1
		go fmt.Sprintf("%v %v", x, y)
		fmt.Println("After")
	}
}

func f5_before() {
	for i := 0; i < 10; i++ {
		x := i
		y := x + 1
		fmt.Println("Before")
		go fmt.Sprintf("%v %v", x, y)
	}
}
func f5_before_after() {
	for i := 0; i < 10; i++ {
		x := i
		y := x + 1
		fmt.Println("Before")
		go fmt.Sprintf("%v %v", x, y)
		fmt.Println("After")
	}
}
