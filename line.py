from rhymetime import RhymeChecker
import re
from random import randint

class Line:

  abbrevs_re = re.compile("\s[BCDEFGHJKLMNOPQRSTUVWXYZ]\s")
  non_alpha_space_or_hyphen_re = re.compile("[^A-Za-z \-']")
  vowels_re = re.compile("aeiouy")

  #lines have text, a rime, and sometimes siblings (if the line comes from a split line-of-text)
  def __init__(self, text, rhyme_checker=None):
    self.text = text

    #cf. http://stackoverflow.com/questions/1132941/least-astonishment-in-python-the-mutable-default-argument
    if rhyme_checker:
      self.rhyme_checker = rhyme_checker
    else:
      self.rhyme_checker = RhymeChecker()

    self.siblings = [[], []]
    self._cleaned_text = None
  def __repr__(self):
    return "<\"" + self.text + "\">"
  def __hash__(self):
    return hash(str(self.text))

  def is_partial(self):
    return not not self.siblings[0] or not not self.siblings[1]
  def before_siblings(self):
    return self.siblings[0]
  def after_siblings(self):
    return self.siblings[1]
  def total_siblings(self):
    return len(self.before_siblings()) + len(self.after_siblings())

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

  def valid(self):
    return not self.clean_text() == ""

  def should_be_skipped(self):
    number_abbrev = "No." in self.text
    other_abbrev = Line.abbrevs_re.search(self.clean_text())
    case_citations = " v." in self.text
    blank = self.clean_text().strip() == ""
    nonwords = False in [Line.vowels_re.search(word) for word in self.clean_text().split(" ")]
    numbers = re.search("[0-9]", self.text)
    return number_abbrev or other_abbrev or case_citations or blank or nonwords or numbers

  def clean_text(self):
    if self._cleaned_text:
      return self._cleaned_text
    #clean_text = re.sub("[^A-Za-z \-']", "", self.text)
    clean_text = Line.non_alpha_space_or_hyphen_re.sub("", self.text)
    #clean_text = re.sub("  +", " ", clean_text)
    clean_text = ' '.join(clean_text.split())
     

    clean_text = clean_text.strip()
    self._cleaned_text = clean_text
    return clean_text

  def split_line_to_format(self, syllable_counts):
    """
    Given a format...

    >>> l = Line("tell me all your thoughts on god because i'd really like to meet her yes")
    >>> l.split_line_to_format([5,7,5])
    [[<"tell me all your thoughts">, <"on god because i'd really">, <"like to meet her yes">]]
    >>> l = Line("a big blue pig flew")
    >>> l.split_line_to_format([(2,3), (2,3)])
    [[<"a big">, <"blue pig flew">], [<"a big blue">, <"pig flew">]]
    >>> l.split_line_to_format([(2,3), (2,3), 7])
    [[<"a big">, <"blue pig flew">], [<"a big blue">, <"pig flew">]]
    >>> l.split_line_to_format([(2,3), (2,3), 1])
    [[<"a big">, <"blue pig">, <"flew">], [<"a big">, <"blue pig flew">], [<"a big blue">, <"pig flew">]]
    """
    # 5,7,5 "tell me all your thoughts on god i would really like to meet her yes no"
              #yes that song came on shuffle while i was writing this

    #what about (2,3), (2,3) for "a big blue pig flies"
    if not syllable_counts:
      if self.clean_text() == "":
        return []
      else:
        return False

    first_syll_count = syllable_counts[0]
    syllable_counts = syllable_counts[1:]
    splits = self.split_line_at_syllable_count(first_syll_count)
    #print "splits: " + str(splits)
    if not splits: #either [] (in base failure case) or False (as it recurses upwards)
      return False

    up_splits = []
    for first_split_line, rest in splits: #e.g. a split at 7 and 8 syllables
      if rest.valid(): #recursion case
        down_splits = rest.split_line_to_format(syllable_counts) 
        #print str(rest) + str(syllable_counts) + " down: " + str(down_splits)

        if down_splits != False: #testing for falsiness isn't enough here.
          #we still need to do this stuff if down_splits is []
          for next_split in down_splits:
            if isinstance(next_split, list):
              up_splits.append( [first_split_line] + next_split )
      else: #base case
        up_splits.append( [first_split_line] )
    #print "up: " + str(up_splits)
    return up_splits


  def split_line_at_syllable_count(self, syllable_count):
    """Returns this Line's text split once at the given number(s) of syllables. 

    returns a list of lists of Line objects, one outer list per item in the
    range in syllable_count 
    E.g. for sentence "a man a plan" and range 1,3, 
    Should this return [["a", "man a plan"], ["a man", "a plan"], ["a man a", "plan"]]?

    >>> r = RhymeChecker()
    >>> l = Line("There once was banana man from the beach", r)
    >>> l.split_line_at_syllable_count(4)
    []
    >>> l = Line("There once was man", r)
    >>> l.split_line_at_syllable_count(4)
    [[<"There once was man">, <"">]]
    >>> l = Line("There once was a man from the beach", r)
    >>> l.split_line_at_syllable_count(4)
    [[<"There once was a">, <"man from the beach">]]
    >>> l = Line("There once was a man from the beach banana", r)
    >>> l.split_line_at_syllable_count(4)
    [[<"There once was a">, <"man from the beach banana">]]
    >>> l = Line("There once was banana people from the beach", r)
    >>> l.split_line_at_syllable_count((5,7))
    [[<"There once was banana">, <"people from the beach">]]
    >>> l = Line("There once was banana man from the beach Anna", r)
    >>> l.split_line_at_syllable_count((5,7))
    [[<"There once was banana">, <"man from the beach Anna">], [<"There once was banana man">, <"from the beach Anna">]]
    """

    if isinstance(syllable_count, int):
      split_texts = [self._split_line_at_syllable_count_helper(self.clean_text(), syllable_count)]
    elif isinstance(syllable_count, tuple):
      split_texts = map(lambda s: self._split_line_at_syllable_count_helper(self.clean_text(), s), \
                        range(syllable_count[0], syllable_count[1]+1))
    elif syllable_count == "any":
      split_texts = map(lambda s: self._split_line_at_syllable_count_helper(self.clean_text(), s), \
                        [randint(5,20), randint(5,20), randint(5,20)] )
    splits_by_syllable_count = map(lambda texts: map(lambda text: Line(text, self.rhyme_checker), texts), filter(lambda x: x is not False, split_texts))
    for split_lines in splits_by_syllable_count:
      #print "a set of splits: " + str(split_lines)
      split_lines = filter(lambda s: s.valid(), split_lines)
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
      if syllable_count == 0:
        return ["", ""]
      else:
        return False
    if syllable_count == 0:
      return ["", line_text]

    elif syllable_count > 0:
      word = split_line[0]
      this_word_syllables = self.rhyme_checker.count_syllables(word)
      next_return = self._split_line_at_syllable_count_helper(" ".join(split_line[1:]), syllable_count - this_word_syllables)
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
    last_word = self.clean_text().split(" ")[-1]
    if "-" in last_word:
      last_word = last_word.split("-")[-1]
    rime = self.rhyme_checker.get_rime(last_word)
    if rime:
      return tuple(rime)
    else:
      #print "No rime for: " + self.clean_text().split(" ")[-1]
      return False


if __name__ == "__main__":
  # import doctest
  # doctest.testmod()
  l = Line("a big blue pig flew")
  print l.split_line_to_format([(2,3), (2,3), 7,8,9])
  print "---------------------"
  l = Line("tell me all your thoughts on god because i'd really like to meet her yes")
  print l.split_line_to_format([5,7,5])


