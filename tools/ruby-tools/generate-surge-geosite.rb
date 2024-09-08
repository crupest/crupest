#!/usr/bin/env ruby
# typed: true
require "sorbet-runtime"
require "set"
require "tmpdir"

extend T::Sig

START_FILES =
  T.let(
    %w[
      github
      google
      youtube
      twitter
      facebook
      discord
      reddit
      twitch
      onedrive
      quora
      telegram
      imgur
      stackexchange

      duckduckgo
      wikimedia
      gitbook
      gitlab
      sourceforge
      creativecommons
      archive
      matrix
      tor

      python
      ruby
      rust
      nodejs
      npmjs
      qt
      docker
      v2ray
      homebrew

      jsdelivr
      fastly
      heroku
      bootstrap
      vercel

      ieee
      sci-hub
      libgen
      z-library
    ],
    T::Array[String]
  )

sig { returns(T::Array[String]) }
def download_data()
  # Create a temp directory
  temp_dir = Dir.mktmpdir

  # download url to temp_dir
  zip_file = File.join(temp_dir, "domain-list-community-master.zip")
  # zip_file = "master.zip"

  url =
    "https://github.com/v2fly/domain-list-community/archive/refs/heads/master.zip"

  `curl -sfL '#{url}' -o #{zip_file}`

  `unzip #{zip_file} -d #{temp_dir}`

  data_dir = File.join(temp_dir, "domain-list-community-master", "data")
  raise "data dir not found" if not Dir.exist?(data_dir)

  [data_dir, temp_dir]
end

class Entry
  extend T::Sig

  sig { params(type: String, value: String, attributes: T::Array[String]).void }
  def initialize(type, value, attributes)
    @type = type
    @value = value
    @attributes = attributes
  end

  attr_reader :type, :value, :attributes

  def to_s
    "#{type},#{value}"
  end
end

# Return nil if the line is a comment or empty
# Return a string if the line is an include
# Return an Entry if the line is a rule
sig { params(line: String).returns(T.nilable(T.any(Entry, String))) }
def handle_line(line)
  line.strip!
  return if line.empty?
  return if line.start_with?("#")

  fields =
    T
      .must(line.split("#")[0])
      .split(" ")
      .map { |s| s.strip }
      .filter { |s| not s.empty? }

  rule = T.let(T.must(fields[0]), String)

  attributes = T.let([], T::Array[String])

  for attribute in T.must(fields[1..])
    if attribute.start_with?("@")
      attributes << T.must(attribute[1..])
    else
      raise "Invalid attribute: #{attribute}"
    end
  end

  type = T.let("", String)
  value = T.let("", String)

  if rule.start_with?("include:")
    return rule["include:".length..]
  elsif rule.start_with?("domain:")
    type = "DOMAIN-SUFFIX"
    value = T.must(rule["domain:".length..])
  elsif rule.start_with?("full:")
    type = "DOMAIN"
    value = T.must(rule["full:".length..])
  elsif rule.start_with?("keyword:")
    type = "DOMAIN-KEYWORD"
    value = T.must(rule["keyword:".length..])
  elsif rule.start_with?("regexp:")
    type = "URL-REGEX"
    value = T.must(rule["regexp:".length..])
  else
    type = "DOMAIN-SUFFIX"
    value = rule
  end

  Entry.new(type, value, attributes)
end

sig do
  params(
    filename: String,
    data_dir: String,
    already_handled_files: T::Set[String],
    entries: T::Array[Entry]
  ).void
end
def handle_file(filename, data_dir, already_handled_files, entries)
  return if already_handled_files.include?(filename)
  already_handled_files.add filename
  file_path = File.join(data_dir, filename)
  # Read as UTF-8
  File.open(file_path, "r:UTF-8") do |file|
    file.each_line() do |line|
      line_result = handle_line(line)
      if line_result.is_a?(Entry)
        entries << line_result
      elsif line_result.is_a?(String)
        handle_file(line_result, data_dir, already_handled_files, entries)
      end
    end
  end
end

sig do
  params(data_dir: String, start_files: T::Array[String]).returns(
    T::Array[Entry]
  )
end
def handle_data(data_dir, start_files)
  already_handled_files = T.let(Set.new, T::Set[String])
  result = T.let([], T::Array[Entry])
  for filename in start_files
    handle_file(filename, data_dir, already_handled_files, result)
  end
  result
end

sig { params(entries: T::Array[Entry]).returns(T::Array[Entry]) }
def get_entries_with_no_attribute(entries)
  entries.filter { |entry| entry.attributes.empty? }
end

sig do
  params(entries: T::Array[Entry], attribute: String).returns(T::Array[Entry])
end
def get_entries_with_attribute(entries, attribute)
  entries.filter { |entry| entry.attributes.include?(attribute) }
end

sig { params(entries: T::Array[Entry]).void }
def print_entries(entries)
  entries.each { |entry| puts entry.to_s }
end

ARGV.length == 1 or raise "Usage: generate-surge-geosite.rb <china|global>"
mode = ARGV[0]
mode == "china" or mode == "global" or raise "Invalid mode: #{mode}"

data_dir, temp_dir = download_data()
entries = handle_data(T.must(data_dir), START_FILES)
print_entries(get_entries_with_no_attribute(entries)) if mode == "global"
print_entries(get_entries_with_attribute(entries, "cn")) if mode == "china"

FileUtils.remove_entry(T.must(temp_dir))
