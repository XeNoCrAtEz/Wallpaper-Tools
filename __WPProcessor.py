# Module to store WPProcessor class
import os
from PIL import Image
import imagehash
import numpy as np
import cv2
import multiprocessing
import itertools
from skimage.metrics import structural_similarity as ssim

# ------ just making a counter for showing image comparisons ------
class Counter():
    def __init__(self ) :
        self.val = multiprocessing.Value('i', 0)
        self.lock = multiprocessing.Lock()
    
    def increment( self ):
        with self.lock :
            self.val.value += multiprocessing.cpu_count()
    
    def value( self ):
        return self.val.value

    def reset( self ) :
        self.val.value = 0
counter = Counter()
# ------ just making a counter for showing image comparisons ------

# class WPProcessor has methods that can help wallpaper processing
class WPProcessor():
    # It needs the directory where the images are (dirname) and the hash size
    # for analyzing the images (hash_size), default is 8
    def __init__( self, dirname, hash_size = 8, similarity_percentage = 80 ):
        self.dirname = dirname
        self.hash_size = hash_size
        self.similarity_percentage = similarity_percentage

        # create a list of all images inside this folder
        self.filenames = os.listdir(self.dirname)
        self.filenames = self.get_img_filenames(self.filenames)     # select image filenames only
        
        # count how many images are inside the folder
        self.imgCount = len(self.filenames)
        if self.imgCount == 0:          # exit if there are no images in the folder
            print("There are no images in this folder!")
            exit()
        
        # a dictionary which stores all the hashes of each images (for similarity detection)
        self.imageHashes = {}
        self.cmprPairsCount = 0

        # for multiprocessing to be continued automatically
        multiprocessing.freeze_support()

    # method for moving filenames inside a list to a folder
    def move_filenames( self, filenames, dstFolder ):
        print('\n\nMoving images to "{}" folder...\n'.format(dstFolder))

        if os.path.isdir(os.path.join(self.dirname, dstFolder)):
            pass
        else :
            print('No folder named "{}"!!'.format(dstFolder))
            print('Creating "{}" folder...'.format(dstFolder))
            os.mkdir(os.path.join(self.dirname, dstFolder))
        
        for imgFilename in filenames:
            if not imgFilename:     # continue if the imgFilename is "None"
                continue
            os.rename( os.path.join(self.dirname, imgFilename), os.path.join(self.dirname, dstFolder, imgFilename) )
            print("{} Moved Succesfully!".format(imgFilename))

    # method for getting image filenames in the folder as a list
    def get_img_filenames( self, filenames ):
        nonImages = []
        # check whether each filename in the list is an image
        # remove all files or folders which is not an image
        for filename in filenames:
            if not filename.endswith( ('.png', '.jpg', '.jpeg') ) :
                nonImages.append(filename)
        for filename in nonImages:
            filenames.remove(filename)
        return filenames            # return the result
            
    # method for finding duplicate image (exactly the same image, but stored 
    # in different filename)
    def find_duplicates( self ):
        hashes = {}         # prepare a dictionary for storing image filename and its hashes
        duplicates = []     # prepare a list for storing duplicate images
        
        counter = 1         # counter for showing progress

        print("Finding duplicates Now!\n")
        # for each image...
        for imgFilename in self.filenames :
            with Image.open(os.path.join(self.dirname, imgFilename)) as image :
                print("{}/{} images scanned...".format(counter, self.imgCount), end="\r")
                counter += 1

                # create a hash for this image...
                temp_hash = imagehash.average_hash( image, self.hash_size )
                if temp_hash in hashes :        # if this hash is already known...
                    # then we found a duplicate!
                    print("\nDuplicate {} \nfound for Image {}!\n".format(imgFilename, hashes[temp_hash]))
                    # mark both of them as duplicates
                    duplicates.append(imgFilename)
                    # this prevent re-marking a filename as a duplicate
                    if hashes[temp_hash] not in duplicates :
                        duplicates.append(hashes[temp_hash])
                else :                          # if no hash match with this one...
                    hashes[temp_hash] = imgFilename   # insert it to the dictionary
        
        # if we have found some duplicate images...
        if duplicates :
            # move the duplicate images to folder "Duplicates"
            self.move_filenames(duplicates, "Duplicates")
        else :
            print("\nNo duplicate images found.")

        print("\nFinding duplicate images done!")
        self.update_filenames()      # update filenames list

    # method for updating again the filenames list of the object
    def update_filenames( self ):
        # create a list of all images inside this folder
        self.filenames = os.listdir(self.dirname)
        self.filenames = self.get_img_filenames(self.filenames)     # select image filenames only
        
        # count how many images are inside the folder
        self.imgCount = len(self.filenames)
        if self.imgCount == 0:          # exit if there are no images in the folder
            print("There are no images in this folder!")
            exit()

    # method for calculating the average hash of an image and then return it as a dictionary
    def calc_all_hash( self ) :
        print("Calculating all the hashes...\n")
        # calculate all the hashes of each filename, and return it as a dictionary
        imgHashPair = {}
        hashCount = 0
        for imgFilename in self.filenames :
            hashCount += 1
            print("{}/{} images calculated...".format(hashCount, self.imgCount),end="\r")
            with Image.open(os.path.join(self.dirname, imgFilename)) as image :
                imgHash = imagehash.average_hash(image, self.hash_size).hash
                imgHashPair[imgFilename] = imgHash
        print("\nDone calculating hashes!\n")
        return imgHashPair

    # method for creating a dictionary that defines which pairs of files will be compared
    # this method is to avoid comparing images to other images that has been compared before
    def get_cmpr_pairs_list( self ):
        cmprPairsList = []
        for i in range(0, self.imgCount):
            for j in range(i+1, self.imgCount):
                cmprPairsList.append( [self.filenames[i], self.filenames[j]] )
        return cmprPairsList
        # example of comparing 4 element to 5 element list
        # all possible comparisons are :
        # 1 -> 1    2 -> 1    3 -> 1    4 -> 1
        # 1 -> 2    2 -> 2    3 -> 2    4 -> 2
        # 1 -> 3    2 -> 3    3 -> 3    4 -> 3
        # 1 -> 4    2 -> 4    3 -> 4    4 -> 4
        # 1 -> 5    2 -> 5    3 -> 5    4 -> 5
        # as you can see comparing 1 to 2 (1 -> 2) should have similar results
        # as comparing 2 to 1 (2 -> 1). So we can remove all those comparisons
        # and comparisons to itself to get something like :
        #
        # 1 -> 2
        # 1 -> 3    2 -> 3
        # 1 -> 4    2 -> 4    3 -> 4
        # 1 -> 5    2 -> 5    3 -> 5    4 -> 5
        # thus the pattern is 1 to 2-5; 2 to 3-5; 3 to 4-5; and 4 to 5

    # method for finding all similar images. There are chances that an image has
    # the same feature, but find_duplicates() couldn't detect it.
    def find_similars_all( self ):
        print("Finding similar images...\n")

        similarImg = []         # a list that stores similar images
        cmprPairsList = self.get_cmpr_pairs_list()      # get the comparison pairs list
        self.cmprPairsCount = len(cmprPairsList)
        self.imageHashes = self.calc_all_hash()         # calculate the hashes of all images

        # create a multiprocess pool
        with multiprocessing.get_context("spawn").Pool() as p :
            print("Total images to compare : {} images\n".format(self.cmprPairsCount))
            # find all similar image and add it to similarImg
            similarImg = p.map(self.compare_img, cmprPairsList)
            # remove all None from the list
            similarImg = list(filter(None, similarImg))
            # melt all the list result into a single list
            # from [[], [], ...] into [ ... ]
            similarImg = itertools.chain.from_iterable(similarImg)
            # remove duplicates
            similarImg = list(dict.fromkeys(similarImg))

        # if we have found some similar images...
        if similarImg:
            self.move_filenames(similarImg, "Similars")
        else :
            print("\nNo similar images found.")

        print("\nDone searching for similar images!")
        self.update_filenames()

    # method for comparing a pair of image. Returns the pair if the two image is similar
    # (the similarity is higher than similarity_percentage) and returns nothing if not
    def compare_img( self, imagePair ):
        # get the pair of image filename that we want to compare
        imgA, imgB = imagePair[0], imagePair[1]
        
        # ------ just making a counter for the image comparisons ------
        counter.increment()
        print("{}/{} images compared...".format(counter.value(), self.cmprPairsCount), end="\r")
        # ------ just making a counter for the image comparisons ------

        # ---- comparison algorithm starts here ----
        # add the threshold
        threshold = 1 - self.similarity_percentage/100
        diff_limit = int(threshold*(self.hash_size**2))
        
        hashA = self.imageHashes[imgA]
        hashB = self.imageHashes[imgB]
        
        result = np.count_nonzero(hashA != hashB) <= diff_limit
        # ---- comparison algorithm stops here ----

        # this part will conclude whether the two image is similar or not
        if result:
            print("{} image found {}% similar to {}".format(imgA, self.similarity_percentage, imgB))
            return imagePair

    # method for finding images that needs to be edited (crop and resize),
    # because the resolution is less than 1080p or the ratio is not 16:9
    def find_need_edits( self ):
        needResizes = []        # a list for storing images that needs to be resized
        needCrops = []          # a list for storing images that needs to be cropped
        needCropsResizes = []   # a list for storing images that needs to be cropped and resized
        # create a multiprocess pool
        with multiprocessing.get_context("spawn").Pool() as p:
            # find all images that needs to be resized only
            needResizes = p.map(self.check_need_resize, self.filenames)
            # move all the images that needs to be edited to "need_resize" folder
            if needResizes :
                self.move_filenames(needResizes, "Need_resize")
            else :
                print("There are no images that needs to be resized")
            self.update_filenames()

            # find all images that needs to be cropped only
            needCrops = p.map(self.check_need_crop, self.filenames)
            # move all the images that needs to be edited to "need_crop" folder
            if needCrops :
                self.move_filenames(needCrops, "Need_crop")
            else :
                print("There are no images that needs to be cropped")
            self.update_filenames()

            # find all images that needs to be cropped and resized
            needCropsResizes = p.map(self.check_need_crop_resize, self.filenames)
            # move all the images that needs to be edited to "need_crop_resize" folder
            if needCropsResizes :
                self.move_filenames(needCropsResizes, "Need_crop_resize")
            else :
                print("There are no images that needs to be cropped and resized")
            self.update_filenames()
        print("\nDone searching for images that needs to be edited!")

    # method for checking whether the image needs to be resized only or not.
    # returns the image if it needs resize. returns nothing if it doesn't.
    # an image needs to be resized if it is less than 1080p but the ratio is 16:9
    def check_need_resize( self, filename ):
        imagePath = os.path.join(self.dirname, filename)
        with Image.open(imagePath) as image:
            ratio = image.width/image.height
            isWithinRatio = (16/9)*98/100 <= ratio <= (16/9)*102/100
            if image.height < 1080 and image.width < 1920 and isWithinRatio:
                return filename

    # method for checking whether the image needs to be cropped only or not
    # returns the image if it needs crop. Returns nothing if it doesn't.
    # an image needs to be resized if it is higher than 1080p but the ratio is not 16:9
    def check_need_crop( self, filename ):
        imagePath = os.path.join(self.dirname, filename)
        with Image.open(imagePath) as image:
            ratio = image.width/image.height
            isWithinRatio = (16/9)*98/100 <= ratio <= (16/9)*102/100
            if image.height >= 1080 and image.width >= 1920 and not isWithinRatio:
                return filename

    # method for checking whether the image needs to be cropped and resized
    def check_need_crop_resize( self, filename ):
        imagePath = os.path.join(self.dirname, filename)
        with Image.open(imagePath) as image:
            ratio = image.width/image.height
            isWithinRatio = (16/9)*98/100 <= ratio <= (16/9)*102/100
            if image.height < 1080 and image.width < 1920 and not isWithinRatio:
                return filename
