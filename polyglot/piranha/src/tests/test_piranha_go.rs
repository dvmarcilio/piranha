/*
Copyright (c) 2022 Uber Technologies, Inc.

 <p>Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file
 except in compliance with the License. You may obtain a copy of the License at
 <p>http://www.apache.org/licenses/LICENSE-2.0

 <p>Unless required by applicable law or agreed to in writing, software distributed under the
 License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 express or implied. See the License for the specific language governing permissions and
 limitations under the License.
*/

use super::{initialize, run_rewrite_test};

static LANGUAGE: &str = "go";

#[test]
fn test_go_structural_replacement() {
  initialize();
  run_rewrite_test(
    &format!("{}/{}", LANGUAGE, "structural_replacement"),
    1,
  );
}

#[test]
fn test_go_replacement_cleanup() {
  initialize();
  run_rewrite_test(
    &format!("{}/{}", LANGUAGE, "replacement_cleanup"),
    1,
  );
}

#[test]
fn test_go_if_replacement_cleanup() {
  initialize();
  run_rewrite_test(
    &format!("{}/{}", LANGUAGE, "if_replacement_cleanup"),
    1,
  );
}
