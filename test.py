from purreader import PURReader
import logging

logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':
    reader = PURReader('COM7')

    # read example parameters
    print('Number of antennas: {}'.format(reader.antCount))
    print('Sensitivity: {} dBm'.format(reader.sensDBm))
    print('Modulation depth: {} %'.format(reader.modDepth))

    # set example parameters
    reader.attnDB = 0
    reader.freqKHz = 866000 # single, static frequency
    #reader.freqKHz = [865700, 866900, 867500, 866300] # hop randomly on ETSI frequencies
    reader.blfKHz = 80 # tag backscatter link frequency
    reader.encoding = 'FM0' # or M2, M4, M8
    reader.session = 2

    # search for tags
    print(reader.singleInventory())
