/**
 * Copyright (c) 2022 Uber Technologies, Inc.
 *
 * <p>Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file
 * except in compliance with the License. You may obtain a copy of the License at
 *
 * <p>http://www.apache.org/licenses/LICENSE-2.0
 *
 * <p>Unless required by applicable law or agreed to in writing, software distributed under the
 * License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 */

package piranha

import (
	"fmt"
)

func main() {
	const notReplaced = "No replace\n"
	const name, age = "Kim", 22
	fmt.Println(name, " is ", age, " years old.")
}

func another() {
	fmt.Print("No replace")
}
