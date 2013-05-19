from rhymetime import RhymeChecker
import re

class Line:
  #lines have text, a rime, and sometimes siblings (if the line comes from a split line-of-text)
  def __init__(self, text, rhyme_checker):
    self.text = text
    self.rhyme_checker = rhyme_checker
    self.siblings = [[], []]
    self._cleaned_text = None
  def __repr__(self):
    return self.text
  def is_partial(self):
    return not not self.siblings[0] or not not self.siblings[1]
  def before_siblings(self):
    return self.siblings[0]
  def after_siblings(self):
    return self.siblings[1]

  #doin' it linked-list style
  def next_sibling(self):
    if len(self.siblings[1]) > 0:
      return self.siblings[1][0]
    else:
      return False
  def prev_sibling(self):
    if len(self.siblings[0]) > 0:
      return self.siblings[0][-1]
    else:
      return False


  def should_be_skipped(self):
    number_abbrev = "No." in self.text
    other_abbrev = re.search("\s[BCDEFGHJKLMNOPQRSTUVWXYZ]\s", self.clean_text())
    case_citations = " v." in self.text
    return number_abbrev or other_abbrev or case_citations

  def clean_text(self):
    if self._cleaned_text:
      return self._cleaned_text
    clean_text = re.sub("[^A-Za-z \-']", "", self.text)
    clean_text = re.sub("  +", " ", clean_text)
    clean_text = clean_text.strip()
    self._cleaned_text = clean_text
    return clean_text

  def split_line_at_syllable_count(self, syllable_count):
    """Returns a list of Line objects containing this Line's text split at the given number(s) of syllables. 

    If a range, return a list of possibilities.
    E.g. for sentence "a man a plan" and range 1,3, 
    Should this return [["a", "man a plan"], ["a man", "a plan"], ["a man a", "plan"]]?

    >>> r = RhymeChecker()
    >>> l = Line("There once was banana man from the beach", r)
    >>> l.split_line_at_syllable_count(4)
    []
    >>> l = Line("There once was a man from the beach", r)
    >>> l.split_line_at_syllable_count(4)
    [['There once was a', 'man from the beach']]
    >>> l = Line("There once was a man from the beach banana", r)
    >>> l.split_line_at_syllable_count(4)
    [['There once was a', 'man from the beach banana']]
    >>> l = Line("There once was banana people from the beach", r)
    >>> l.split_line_at_syllable_count((5,7))
    [['There once was banana', 'people from the beach']]
    >>> l = Line("There once was banana man from the beach Anna", r)
    >>> l.split_line_at_syllable_count((5,7))
    [['There once was banana', 'man from the beach Anna'], ['There once was banana man', 'from the beach Anna']]
    """

    if isinstance(syllable_count, int):
      split_texts = [self._split_line_at_syllable_count_helper(self.clean_text(), syllable_count)]
    elif isinstance(syllable_count, tuple):
      split_texts = map(lambda s: self._split_line_at_syllable_count_helper(self.clean_text(), s), range(syllable_count[0], syllable_count[1]+1))
    splits_by_syllable_count = map(lambda texts: map(lambda text: Line(text, self.rhyme_checker), texts), filter(lambda x: x is not False, split_texts))
    for split_lines in splits_by_syllable_count:
      for i, split_line in enumerate(split_lines):
        split_line.siblings[0] = split_lines[0:i]
        split_line.siblings[1] = split_lines[(i+1):]
        #each split line's siblings are all of the other lines split from the same "parent" with same syll count.
        #these siblings must appear sequentially in a poem or not at all. 
        #(So we don't little incoherent bits and pieces of sentences everywhere.)
    return splits_by_syllable_count or []

  def _split_line_at_syllable_count_helper(self, line_text, syllable_count):
    split_line = line_text.split(" ")
    if "" in split_line:
      return False
    if syllable_count == 0:
      return ["", line_text]
    elif syllable_count > 0:
      word = split_line[0]
      this_word_syllables = self.rhyme_checker.count_syllables(word)
      next_return =  self._split_line_at_syllable_count_helper(" ".join(split_line[1:]), syllable_count - this_word_syllables)
      if next_return:
        next_return[0] = " ".join([word] + filter(lambda x: x != "", next_return[0].split(" ")))
        return next_return
      else:
        return False
    else:
      return False

  def syllable_count(self):
    """return this line's syllable count to use as key to this value in the syllable_count hash."""
    return sum(map(self.rhyme_checker.count_syllables, self.clean_text().split(" ")))

  def rime(self):
    """Return this line's last word's rime to use as key to this value in the rhyme hash."""
    rime = self.rhyme_checker.get_rime(self.clean_text().split(" ")[-1])
    if rime:
      return tuple(rime)
    else:
      return False


if __name__ == "__main__":
  import doctest
  doctest.testmod()
