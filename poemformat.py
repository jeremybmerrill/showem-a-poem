#!/usr/bin/python
# -*- coding: utf-8 -*-

class PoemFormat(object):
  syllable_structure = None
  rhyme_scheme = None
  lines_needed = 0
  lines = [None] * lines_needed
  _filled_out_format = None 

  def get_format(self):
    return self._filled_out_format or self.fill_out_format()

  def fill_out_format(self):
    format = {}
    if self.rhyme_scheme:
      format["rhyme_scheme"] = self.rhyme_scheme
    if self.lines_needed:
      format["lines_needed"] = self.lines_needed
    if self.syllable_structure:
      format["syllable_structure"] = self.syllable_structure

    #create lines_needed if not present
    if "lines_needed" not in format:
      format["lines_needed"] = max(len(format["syllable_structure"]), len(format["rhyme_scheme"]))
    lines_needed = format["lines_needed"]

    #create rhyme_scheme if not present; fill it out if present.
    if "rhyme_scheme" not in format:
      format["rhyme_scheme"] = "abcdefghijklmnopqrstuvwxyz"[0:format["lines_needed"]]
    else:
      format["rhyme_scheme"] = format["rhyme_scheme"] * (lines_needed / len(format["rhyme_scheme"]))

    #create syllable_structure if not present; fill it out if present
    if "syllable_structure" in format:
      if len(format["syllable_structure"]) < lines_needed:
        multiple = float(lines_needed) / len(format["syllable_structure"])
        if multiple % 1.0 != 0.0:
          raise TypeError, "Invalid poem format :("
        format["syllable_structure"] = int(multiple) * format["syllable_structure"]
    else:
      format["syllable_structure"] = ['any'] * format["lines_needed"]

    #fill out rhyme_scheme if not the right length
    if len(format["rhyme_scheme"]) < lines_needed:
      multiple = float(lines_needed) / len(format["rhyme_scheme"])
      if multiple % 1.0 != 0.0:
        raise TypeError, "Invalid poem format :("
      format["rhyme_scheme"] = int(multiple) * format["rhyme_scheme"]

    #create unique_syllable_structure
    format["unique_syllable_structure"] = set()
    for syllable_count_item in format["syllable_structure"]:
      format["unique_syllable_structure"].add(syllable_count_item)

    #create syllable_count_to_syllable_count_token, which maybe can #TODO be factored out.
    format["syllable_count_to_syllable_count_token"] = {}
    for syllable_count_item in format["syllable_structure"]:
      if isinstance(syllable_count_item, int):
        if syllable_count_item not in format["syllable_count_to_syllable_count_token"].keys():
          format["syllable_count_to_syllable_count_token"][syllable_count_item] = set()
        format["syllable_count_to_syllable_count_token"][syllable_count_item].add(syllable_count_item)
      elif isinstance(syllable_count_item, tuple):
        for num in range(syllable_count_item[0],syllable_count_item[1]+1):
          if num not in format["syllable_count_to_syllable_count_token"].keys():
            format["syllable_count_to_syllable_count_token"][num] = set()
          format["syllable_count_to_syllable_count_token"][num].add(syllable_count_item)
      elif syllable_count_item == "any":
        if syllable_count_item not in format["syllable_count_to_syllable_count_token"].keys():
          format["syllable_count_to_syllable_count_token"][syllable_count_item] = set()
        format["syllable_count_to_syllable_count_token"][syllable_count_item].add(syllable_count_item)

    self._filled_out_format = format
    return format

  def format_poem(self, lines):
    return "\n".join([("" if (line is None) else line.text) for line in lines])

  def sing(self):
    #TODO: write this.
    class NotYetImplementedError(Exception):
      pass
    raise NotYetImplementedError



class Haiku(PoemFormat):
  syllable_structure = [5,7,5]
  rhyme_scheme = "abc"

class Freeverse(PoemFormat):
  def __init__(self, lines_needed=10):
    self.lines_needed = lines_needed

class Limerick(PoemFormat):
  syllable_structure = [(9,11),(9, 11),6,6,(9, 11)]
  rhyme_scheme = "aabba"

class Sonnet(PoemFormat):
  syllable_structure = [10]
  rhyme_scheme = "ababcdcdefefgg"

class Song(PoemFormat):
  syllable_structure = [(5,10)]
  rhyme_scheme = "aabbccddeeff" #"ababcdcdefefghghijij" #"aabbccddeeff"
  def format_poem(self, lines):
    chorus = lines[0:4]
    verse1 = lines[4:8]
    verse2 = lines[8:12]
    verse3 = lines[12:16]
    verse4 = lines[16:]
    song = verse1 + [""] + chorus + [""] + verse2 + [""] + chorus + [""] + verse3 + [""] + chorus + [""] + verse4
    return "\n  ".join(["" if line == None else line.text for line in lines])
