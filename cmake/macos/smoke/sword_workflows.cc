// SPDX-License-Identifier: GPL-2.0-or-later
// Exercises SWORD storage/search, not the GTK editor or search dialog.
#include <swmgr.h>
#include <swmodule.h>
#include <listkey.h>
#include <rawfiles.h>
#include <iostream>
#include <stdexcept>
#include <string>

static void require(bool ok, const char *message)
{
    if (!ok) throw std::runtime_error(message);
}

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    try {
        sword::SWMgr manager(argv[1], true, nullptr, false, false);
        auto *module = manager.getModule("BuildFixture");
        require(module != nullptr, "fixture module missing");
        module->setKey("Genesis 1:1");
        require(std::string(module->getRawEntry()).find("Apple Silicon") != std::string::npos,
                "first verse mismatch");
        module->setKey("Genesis 1:2");
        require(std::string(module->getRawEntry()).find("nearby verse references") != std::string::npos,
                "second verse mismatch");
        module->setKey("John 1:1");
        require(std::string(module->getRawEntry()).find("another book") != std::string::npos,
                "cross-book verse mismatch");
        require(module->search("Apple Silicon", -1).getCount() == 1,
                "phrase search should find one entry");
        require(module->search("original", -1).getCount() == 3,
                "phrase search should find three entries");
        require(module->search("absent_test_token_92741", -1).getCount() == 0,
                "absent search should return no entries");
        std::string directory = std::string(argv[2]) + "/";
        const std::string note = "Original test note: caf\xC3\xA9, \xCE\xB1\xCE\xB2\xCE\xB3.\nSecond line.";
        require(sword::RawFiles::createModule(directory.c_str()) == 0,
                "could not create notes module");
        {
            sword::RawFiles notes(directory.c_str(), "FixtureNotes");
            require(notes.isWritable(), "notes module is not writable");
            notes.setKey("Genesis 1:1");
            notes.setEntry(note.c_str());
        }
        {
            sword::RawFiles notes(directory.c_str(), "FixtureNotes");
            notes.setKey("Genesis 1:1");
            require(std::string(notes.getRawEntry()) == note,
                    "UTF-8 note did not survive module reopen");
        }
        std::cout << "SWORD verse lookup, phrase search (1/3/0 hits), and UTF-8 RawFiles note reopen passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
