import __WPProcessor
import os
import sys

if __name__ == "__main__":
    dirname = os.getcwd()
    WPObj = __WPProcessor.WPProcessor( dirname, 64, 80 )
    # if we want to find duplicate images, we give argument "1" from cmd
    if sys.argv[1] == "1":
        WPObj.find_duplicates()
    # if we want to find similar images, we give argument "2" from cmd
    if sys.argv[1] == "2":
        WPObj.find_similars_all()
    # if we want to find images that needs to be edited, we give argument "3" from cmd
    if sys.argv[1] == "3":
        WPObj.find_need_edits()
    input("\n\nPress any key to close the program...")