"""Unit tests for changelog validator"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "action", "src"))

import unittest

from changelog_validator import ChangelogValidator


class TestChangelogValidator(unittest.TestCase):
    """Test cases for ChangelogValidator"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = ChangelogValidator()

    def test_valid_minimal_entry(self):
        """Test validation of minimal valid entry"""
        yaml_content = """
title: Add new feature
type: added
authors:
  - name: John Developer
    nick: john
    url: https://github.com/john
"""
        is_valid, errors = self.validator.validate(yaml_content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_missing_title(self):
        """Test validation fails when title is missing"""
        yaml_content = """
type: added
authors:
  - name: John Developer
    nick: john
"""
        is_valid, errors = self.validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertIn("Missing mandatory field: title", errors)

    def test_invalid_yaml(self):
        """Test validation fails for invalid YAML"""
        yaml_content = """
title: Test
  invalid indentation:
    - bad
"""
        is_valid, errors = self.validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid YAML" in e for e in errors))

    def test_invalid_type(self):
        """Test validation fails for invalid type"""
        yaml_content = """
title: Test
type: invalid_type
"""
        is_valid, errors = self.validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid type" in e for e in errors))

    def test_forbidden_field(self):
        """Test validation fails when forbidden field is present"""
        validator = ChangelogValidator(forbidden_fields=["internal"])
        yaml_content = """
title: Test
type: added
internal: true
"""
        is_valid, errors = validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertIn("Forbidden field present: internal", errors)

    def test_empty_yaml(self):
        """Test validation fails for empty YAML"""
        is_valid, errors = self.validator.validate("")
        self.assertFalse(is_valid)
        self.assertIn("YAML is empty", errors)

    def test_not_dict_yaml(self):
        """Test validation fails when YAML is not a dict"""
        yaml_content = "- item1\n- item2"
        is_valid, errors = self.validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertIn("YAML must be a dictionary/object", errors)

    def test_invalid_authors(self):
        """Test validation fails for invalid authors"""
        yaml_content = """
title: Test
authors:
  - nick_only: john
"""
        is_valid, errors = self.validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertTrue(any('missing or empty "name"' in e for e in errors))

    def test_custom_mandatory_fields(self):
        """Test validation with custom mandatory fields"""
        validator = ChangelogValidator(mandatory_fields=["title", "type", "authors"])
        yaml_content = """
title: Test
type: added
"""
        is_valid, errors = validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertIn("Missing mandatory field: authors", errors)

    def test_custom_types(self):
        """Test validation with custom changelog types"""
        validator = ChangelogValidator(changelog_types=["feature", "bugfix"])
        yaml_content = """
title: Test
type: feature
"""
        is_valid, errors = validator.validate(yaml_content)
        self.assertTrue(is_valid)

        yaml_content = """
title: Test
type: added
"""
        is_valid, errors = validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid type" in e for e in errors))

    def test_optional_fields_restriction(self):
        """Test validation with restricted optional fields"""
        validator = ChangelogValidator(optional_fields=["title", "type", "authors"])
        yaml_content = """
title: Test
type: added
modules:
  - api
"""
        is_valid, errors = validator.validate(yaml_content)
        self.assertFalse(is_valid)
        self.assertTrue(any("Unknown field: modules" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
