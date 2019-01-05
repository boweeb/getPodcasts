#! /usr/bin/env python3

"""
Notes:
Simple podcast downloader
- gets the rss
- gets the url
- downloads the most recent episode
- edits the metadata

written by Jonathan Ayers
https://github.com/jfayerz/get_podcasts
"""
# TODO:
#   - option to continue scrolling down list of episodes after downloading
#       your first selection

import sys
import re
import feedparser as fp
import urllib
import configparser as cp
from datetime import date
from mutagen.id3 import ID3NoHeaderError
from mutagen.id3 import ID3
from mutagen.id3 import TIT2, TALB, TPE1, TPE2, TRCK, TPOS

user_options = len(sys.argv)
todays_date = str(date.today())
path_to_configuration_file = ''
configuration_settings_file = 'pod_config'
history_file = 'pod_history'
# rss_parameters_from_file = 'rssparams'  # this isn't needed any longer
config = cp.ConfigParser()
history = cp.ConfigParser()
config.read(path_to_configuration_file + configuration_settings_file)
history.read(path_to_configuration_file + history_file)
config_sections = config.sections()
history_sections = history.sections()


def get_podcasts(config_sections, history_sections):
    for podcast_entry in config_sections:
        if todays_date != history[podcast_entry]['last_downloaded_date']:
            print("Getting rss info for " + podcast_entry + ".")
            rss = fp.parse(config[podcast_entry]['rss'])
            if config[podcast_entry]['podpath'] != "":
                pod_path = config[podcast_entry]['podpath']
            else:
                pod_path = ''
            episode_number_parameters = config.get(podcast_entry, 'episode_parameters')
            if episode_number_parameters != '':
                episode_params = episode_number_parameters.split(',')

            season_number_parameters = config.get(podcast_entry, 'season_parameters')
            if season_number_parameters != '':
                season_params = season_number_parameters.split(',')

            title = []
            title_formatted_white_space_removed = rss.entries[0].title.strip()
            title.append(title_formatted_white_space_removed)
            file_name = []
            title_to_filename = re.sub('/', ' ', title[0]) + ".mp3"
            file_name.append(title_to_filename)
            artist = config[podcast_entry]['artist']
            album = config[podcast_entry]['album']
            album_artist = config[podcast_entry]['album_artist']
            last_url = history[podcast_entry]['last_url']
            does_this_link_contain_mp3 = rss.entries[0].links[0].href.find(".mp3")
            url = []
            if does_this_link_contain_mp3 != -1:
                if rss.entries[0].links[0].href.find(".mp3", (does_this_link_contain_mp3 + 4)) != -1:
                    what_about_this_link = rss.entries[0].links[0].href.find(".mp3", (does_this_link_contain_mp3 + 4))
                    url.append(rss.entries[0].links[0].href[0:(what_about_this_link + 4)])
                else:
                    url.append(rss.entries[0].links[0].href[0:(does_this_link_contain_mp3 + 4)])
            else:
                try:
                    does_this_link_contain_mp3 = rss.entries[0].links[1].href.find(".mp3")
                except IndexError:
                    continue
                if rss.entries[0].links[1].href.find(".mp3", (does_this_link_contain_mp3 + 4)) != -1:
                    what_about_this_link = rss.entries[0].links[1].href.find(".mp3", (does_this_link_contain_mp3 + 4))
                    url.append(rss.entries[0].links[1].href[0:(what_about_this_link + 4)])
                else:
                    url.append(rss.entries[0].links[1].href[0:(does_this_link_contain_mp3 + 4)])

            if config[podcast_entry]['episode_location'] == '':
                if config[podcast_entry]['epnum'] == 'no':
                    episode_num = ''
                else:
                    try:
                        episode_num = rss.entries[0].itunes_episode
                    except KeyError:
                        episode_num = ''
            elif config[podcast_entry]['episode_location'] == 'title':
                episode_num = get_episode_or_season_num(title, episode_params)
            else:
                episode_num = get_episode_or_season_num(url, episode_params)

            if config[podcast_entry]['season_location'] == '':
                if config[podcast_entry]['snnum'] == 'no':
                    season_num = ''
                else:
                    try:
                        season_num = rss.entries[0].itunes_season
                    except KeyError:
                        season_num = ''
            elif config[podcast_entry]['season_location'] == 'title':
                season_num = get_episode_or_season_num(title, season_params)
            else:
                episode_num = get_episode_or_season_num(url, season_params)

            if podcast_entry in history_sections:
                if url[0] != last_url:
                    history[podcast_entry]['last_url'] = url[0]
                    history[podcast_entry]['last_downloaded_date'] = todays_date
                    with open(path_to_configuration_file + history_file, 'w') as pH:
                        history.write(pH)
                    print("Downloading " + title[0] + " from the " + podcast_entry + " podcast.")
                    if pod_path != "":
                        try:
                            urllib.request.urlretrieve(url[0], pod_path + file_name[0])
                            write_id3_single_file(pod_path, file_name[0], title[0], episode_num, season_num, album, album_artist, artist)
                        except urllib.error.HTTPError:
                            print("Download error with " + title[0] + " episode.")
                            continue
                    else:
                        try:
                            urllib.request.urlretrieve(url[0], pod_path + file_name[0])
                            write_id3_single_file(pod_path, file_name[0], title[0], episode_num, season_num, album, album_artist, artist)
                        except urllib.HTTPError:
                            print("Download error with " + title[0] + " episode.")
                            continue
                    # write_id3(pod_path, file_name, title, episode_num, season_num, album, album_artist, artist)
                    # old "write_id3"
                else:
                    print("Already Downloaded " + podcast_entry + " episode.")
            else:
                print("Error")
        else:
            print("Already checked " + config[podcast_entry]['album'] + " podcast today.")


def get_parsed_rss(rss_url):

    rss = fp.parse(rss_url)
    parsed_rss_titles = []
    count_goes_up = 0
    while count_goes_up <= (len(rss.entries) - 1):
        parsed_rss_titles.append(rss.entries[count_goes_up].title)
        count_goes_up += 1
    return rss, parsed_rss_titles


def selection_options(rss_feed_list):

    count_goes_down = len(rss_feed_list)
    selection_list = ["n"]
    while count_goes_down > 0:
        number_to_string_option = str(count_goes_down)
        selection_list.append(number_to_string_option)
        count_goes_down -= 1
    return selection_list   # returns list populated with options from 1 through the last option plus 'n'


def display_five(count_number_of_options, options_from_rss_feed, rss, podcast_name, multiples_of_five, remainder):

    if options_from_rss_feed > len(rss.entries):
        print("You've Reached the Maximum",
              "\nStarting from the beginning of the list.")
        multiples_of_five = int((len(rss.entries) / 5))
        count_number_of_options = 0
        return count_number_of_options, multiples_of_five
    else:
        number_of_eps = len(rss.entries)
        print("Episodes from " + podcast_name + " Podcast",
              "\nThere are currently " + str(number_of_eps) + " Episodes",
              " for this Podcast rss.")
        while count_number_of_options < options_from_rss_feed:
            print("[" + str(count_number_of_options + 1) + "] - " + rss.entries[count_number_of_options].title)
            count_number_of_options += 1
        multiples_of_five -= 1
        return count_number_of_options, multiples_of_five


def a_plus_five(count_number_of_options, multiples_of_five, remainder):

    if multiples_of_five == 0:
        options_from_rss_feed = (count_number_of_options + remainder)
    else:
        options_from_rss_feed = (count_number_of_options + 5)
    return options_from_rss_feed


def enter_selection(selection_list, rss, section_name):

    remainder = int(len(rss.entries) % 5)
    multiples_of_five = int((len(rss.entries) / 5))
    count_number_of_options = 0
    if multiples_of_five < 5:
        options_from_rss_feed = remainder
    else:
        options_from_rss_feed = 5
    selection = 'm'
    while selection.lower() == 'm':
        count_number_of_options, multiples_of_five = display_five(count_number_of_options,
                                                                  options_from_rss_feed,
                                                                  rss,
                                                                  section_name,
                                                                  multiples_of_five,
                                                                  remainder)

        options_from_rss_feed = a_plus_five(count_number_of_options,
                                            multiples_of_five,
                                            remainder)
        print("Enter the number of the podcast episode you wish to download.",
              "\nOr enter \"m\" for [m]ore episodes,\n",
              "\"n\" for the next podcast,\n",
              "\"q\" to quit application.")
        selections = input("Enter your selection here: ")
        set_of_selections = set()
        for selection in selections.split(","):
            selections_split_by_dash = selection.split("-")
            if len(selections_split_by_dash) == 2:
                set_of_selections.update(set(range(int(selections_split_by_dash[0]),
                                                   int(selections_split_by_dash[1])+1)))
            else:
                if selections_split_by_dash[0].isalpha():
                    set_of_selections.add(selections_split_by_dash[0])
                else:
                    set_of_selections.add(int(selections_split_by_dash[0]))
    list_of_selections = list(set_of_selections)
    if list_of_selections[0] == 'n':  # checks for 'n' in the first spot and returns list
        return list_of_selections
    elif list_of_selections[0] == 'q':  # checks for 'q' in the first spot and returns list
        return list_of_selections
    else:
        for selection in list_of_selections:
            if selection > len(rss.entries):  # checks to see if the number or letter they typed is out of range
                print("Your selection is out of range")
                sys.exit()
            else:
                return list_of_selections
            # if the first spot is not a letter, and if all spots
            # are in range then this returns the parsed list of
            # numeric selections back to the primary function


def get_selection_url_title(list_options, rss):

    url = []
    title = []
    for item in list_options:
        title.append(rss.entries[item - 1].title)
        position = rss.entries[item - 1].links[0].href.find(".mp3")
        x = rss.entries[item - 1].links[0].href
        try:
            y = rss.entries[item - 1].links[1].href
        except IndexError:
            pass
        if position != -1:
            if x.find(".mp3", (position + 4)) != -1:
                position2 = x.find(".mp3", (position + 4))
                url.append(x[0:(position2 + 4)])
            else:
                url.append(x[0:(position + 4)])
        else:
            position = y.find(".mp3")
            if y.find(".mp3", (position + 4)) != -1:
                position2 = y.find(".mp3", (position + 4))
                url.append(y[0:(position2 + 4)])
            else:
                url.append(y[0:(position + 4)])
    # print(url, title) # for testing
    return url, title

"""
                        returns a list with the mp3 download url of
                        the selection and the title of the selection
                        TODO: eventually add the ability to select more than
                        one
"""

def get_episode_or_season_num(urltitle_list, parameters):

    # function to get episode number from non standard location
    foo1 = parameters[0]
    bar1 = int(parameters[1])
    foo2 = parameters[2]
    bar2 = int(parameters[3])
    num_list = []
    for x in urltitle_list:
        left_part = x.partition(foo1)[bar1]
        num_list.append(re.sub('[A-Za-z]', '', left_part.partition(foo2)[bar2]).strip())
    return num_list


def write_id3(pod_path, file_name, titles, episode_num, season_num, alb, albart, art):

    print(season_num)
    for file_name_entry in file_name:
        file_name_index = file_name_entry.index(file_name_entry)
        try:
            audio = ID3(pod_path + file_name_entry)
            audio.delete()
            audio = ID3()
        except ID3NoHeaderError:
            audio = ID3()
        audio.add(TIT2(encoding=3, text=titles[file_name_index]))
        if len(episode_num) != 0:
            audio.add(TRCK(encoding=3, text=episode_num[file_name_index]))
        else:
            print("No Ep Num")
        if len(season_num) != 0:
            audio.add(TPOS(encoding=3, text=season_num[file_name_index]))
        else:
            print("No Sn Num")
        audio.add(TPE1(encoding=3, text=art))
        audio.add(TPE2(encoding=3, text=albart))
        audio.add(TALB(encoding=3, text=alb))
        audio.save(pod_path + file_name_entry)


def write_id3_single_file(path, filename, title, episode, season, album, album_artist, artist):
    print(episode)
    print(season)
    try:
        audio = ID3(path + filename)
        audio.delete()
        audio = ID3()
    except ID3NoHeaderError:
        audio = ID3()

    audio.add(TIT2(encoding=3, text=title))
    if episode != '':
        audio.add(TRCK(encoding=3, text=episode))
    else:
        print('No Episode Number')

    if season != '':
        audio.add(TPOS(encoding=3, text=season))
    else:
        print('No Season Number')

    audio.add(TPE1(encoding=3, text=artist))
    audio.add(TPE2(encoding=3, text=album_artist))
    audio.add(TALB(encoding=3, text=album))
    audio.save(path + filename)


def download_selection(pod_path, url_list, title_list, history_info, item, episode, season, artist, album, album_artist):
    """
    print(episode)
    print(season)
    episode_numbers_list = list(map(int, episode))
    season_numbers_list = list(map(int, season))
    print(episode_numbers_list)
    print(season_numbers_list)
    """
    file_names = []
    if len(url_list) > 1:
        count_goes_up = 0
        while count_goes_up < len(url_list):
            print("Downloading episode: ", title_list[count_goes_up])
            title_formatted = re.sub("/", "", title_list[count_goes_up])
            file_names.append(title_formatted + ".mp3")
            urllib.request.urlretrieve(
                url_list[count_goes_up],
                pod_path +
                file_names[count_goes_up])
            print("Downloaded ", title_formatted)
            write_id3_single_file(pod_path, file_names[count_goes_up], title_formatted,
                                  episode[count_goes_up], season[count_goes_up], album, album_artist, artist)
            count_goes_up += 1
    else:
        if history_info[item]['last_downloaded_date'] == todays_date:
            print("Already checked " + item + " podcast today.")
        elif history_info[item]['last_url'] == url_list[0]:
            print("Already downloaded this episode: ", title_list[0])
        else:
            print("Downloading episode: ", title_list[0])
            title_formatted = re.sub("/", "", title_list[0])
            file_names.append(title_formatted + ".mp3")
            urllib.request.urlretrieve(
                url_list[0],
                pod_path +
                file_names[0])
            write_id3_single_file(pod_path, file_names[count_goes_up], title_formatted,
                                  episode[count_goes_up], season[count_goes_up], album, album_artist, artist)
            history_info[item]['last_url'] == url_list[0]
            history_info[item]['last_downloaded_date'] == todays_date
            with open(history_file, 'w') as hist:
                history_info.write(hist)
    return file_names


def primary_function(delim1, delim2, config):

    for podcast_entry in config.sections()[delim1:delim2]:  # If you choose [A] this will go through all of the podcasts
                                                            # in the list even if you download some episodes for some
                                                            # (it assumes 'n' after that point and moves to the next
                                                            # podcaspodcast in the config file).
        rss_url = config[podcast_entry]['rss']
        rss, parsed_rss_titles = get_parsed_rss(rss_url)
        selection_list = selection_options(parsed_rss_titles)
        list_of_selections = enter_selection(selection_list, rss, podcast_entry)
        if isinstance(list_of_selections[0], str) and list_of_selections[0].lower() == 'n':
            delim1 += 1
            delim2 = (delim1 + 1)
            if delim1 >= len(config.sections()):
                print("End of the line, buckaroo!",
                      "\nCome back soon!")
                sys.exit()
            else:
                print("Next Podcast Coming Right Up!")
                primary_function(delim1, delim2, config)
        elif isinstance(list_of_selections[0], str) and list_of_selections[0].lower() == 'q':
            print("Thanks for using my app!")
            sys.exit()
        else:
            season_num_list = []
            url, title = get_selection_url_title(list_of_selections, rss)
            number_options = len(list_of_selections)

            episode_number_parameters = config.get(podcast_entry, "episode_parameters")
            episode_num_list = []

            if episode_number_parameters != "":                    # checking to see if the parameters
                episode_params = episode_number_parameters.split(",")       # option under the selection is populated

            if config[podcast_entry]['episode_location'] == '':  # checks to see where the ep# is located
                if config[podcast_entry]['epnum'] == 'no':   # no episode number indicated
                    episode_num_list.append('')
                else:
                    count_goes_up = 0
                    while count_goes_up < number_options:
                        selection_from_list = list_of_selections[count_goes_up]
                        episode_num_list.append(rss.entries[selection_from_list].itunes_episode)
                        count_goes_up += 1
            elif config[podcast_entry]['episode_location'] == 'title':  # is item set to "title" for pod ep
                episode_num_list = get_episode_or_season_num(title, episode_params)  # TODO update function
            else:                                           # to handle a list
                episode_num_list = get_episode_or_season_num(url, episode_params)  # gets ep from url

            season_number_parameters = config.get(podcast_entry, 'season_parameters')
            season_num_list = []

            if season_number_parameters != '':
                season_params = season_number_parameters.split(',')

            if config[podcast_entry]['season_location'] == '':
                if config[podcast_entry]['snnum'] == 'no':
                    season_num_list.append('')
                else:
                    count_goes_up = 0
                    while count_goes_up < number_options:
                        selection_from_list = list_of_selections[count_goes_up]
                        season_num_list.append(rss.entries[selection_from_list].itunes_season)
                        count_goes_up += 1
            elif config[podcast_entry]['season_location'] == 'title':
                season_num_list = get_episode_or_season_num(title, season_params)
            else:
                season_num_list = get_episode_or_season_num(url, season_params)
            """
            if config[podcast_entry]['snnum'] == 'yes':
                count_goes_up = 0
                while count_goes_up < number_options:
                    selection_from_list = list_of_selections[count_goes_up]
                    season_num_list.append(rss.entries[selection_from_list].itunes_season)
                    count_goes_up += 1
            else:
                season_num_list = []
            """

            artist = config[podcast_entry]['artist']
            album = config[podcast_entry]['album']
            album_artist = config[podcast_entry]['album_artist']

            if config[podcast_entry]['podpath'] != "":       # get path for saving .mp3
                pod_path = config[podcast_entry]['podpath']
            else:
                pod_path = ""
            file_name_list = download_selection(pod_path, url, title, history, podcast_entry, episode_num_list,
                                                season_num_list, artist, album, album_artist)
            # write_id3(pod_path, file_name_list, title, episode_num_list, season_num_list, album, album_artist, artist)
            # Old "write_id3"
            print("File Saved.\nMetadata written.\n")


if user_options != 1:
    if sys.argv[1].lower() == '-h' or sys.argv[1].lower() == '--help':
        print("get_podcasts - https://github.com/jfayers/get_podcasts/",
              "\n\n\tOptions\t\tDescription",
              "\n\n\t-h, --help\t\tThis help screen",
              "\n\t-m, --menu\t\tGives menu options",
              "\n\n\tDefault: No Arguments",
              "\n\t\tProceed with auto download",
              "\n\t\tof newest episodes.")
    elif sys.argv[1].lower() == '-m' or sys.argv[1].lower() == '--menu':
        all_or_one = input("[A]ll podcasts or [C]hoose from list? ")
        if isinstance(all_or_one, str) and all_or_one.lower() == 'c':
            count_goes_up = 0
            while count_goes_up < len(config.sections()):
                print("[" + str(count_goes_up + 1) + "] - " + config.sections()[count_goes_up])
                count_goes_up += 1
            choice = int(input("Choose One: ")) - 1
            choice2 = choice + 1
            primary_function(choice, choice2, config)
        else:
            choice = 0
            choice2 = len(config.sections())
            primary_function(choice, choice2, config)
    else:
        print("Invalid Option\nuse \"-h\" for help")
else:
    get_podcasts(config_sections, history_sections)
