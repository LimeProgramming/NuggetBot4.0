from configparser import ConfigParser
from .exceptions import HelpfulError

class DatabaseLogin:
    def __init__(self):
        config = ConfigParser(interpolation=None)
        config.read("dblogin.ini", encoding='utf-8')

        self.name = config.get('Database', 'database_name', fallback=None)
        self.user = config.get('Database', 'database_user', fallback=None)
        self.pwrd = config.get('Database', 'database_pass', fallback=None)
        self.host = config.get('Database', 'database_host', fallback=None)

        self.run_checks()

    def run_checks(self):
        if not self.name:
            raise HelpfulError(
                "No database name was set",
                "Set one",
                preface="An error has occurred reading the dblogin file"
            )
        if not self.user:
            raise HelpfulError(
                "No username for the database was set",
                "Set one",
                preface="An error has occurred reading the dblogin file"
            )
        if not self.pwrd:
            raise HelpfulError(
                "No password for the database was set",
                "Set one",
                preface="An error has occurred reading the dblogin file"
            )

        if not self.host:
            raise HelpfulError(
                "No host for the database was set",
                "Set one",
                preface="An error has occurred reading the dblogin file"
            )

class DatabaseCmds(object):
    ### ============================== MESSAGES TABLE ==============================
        CREATE_MSGS_TABLE =         """ 
                                    CREATE TABLE IF NOT EXISTS messages (
                                        msg_id BIGINT PRIMARY KEY,
                                        ch_id BIGINT NOT NULL,
                                        srv_id BIGINT NOT NULL,
                                        auth_id BIGINT,
                                        timestamp TIMESTAMP NOT NULL,
                                        num BIGSERIAL
                                        ); 
                                    """
        #add_to_messages =                           
        ADD_MSG =                   """ 
                                    INSERT INTO messages(
                                        msg_id, 
                                        ch_id, 
                                        srv_id,
                                        auth_id, 
                                        timestamp)
                                    VALUES( CAST($1 AS BIGINT), 
                                            CAST($2 AS BIGINT), 
                                            CAST($3 AS BIGINT), 
                                            CAST($4 AS BIGINT), 
                                            $5)
                                    ON CONFLICT (msg_id)
                                        DO NOTHING;
                                    """

        get_messages_after =        "SELECT * FROM messages WHERE timestamp < $1"
        GET_MEMBER_MSGS_AFTER=      "SELECT * FROM messages WHERE auth_id = CAST($1 AS BIGINT) AND timestamp > $2"
                                    #bigger date first
        GET_MEMBER_MSGS_BETWEEN=    "SELECT * FROM messages WHERE auth_id = CAST($1 AS BIGINT) AND timestamp < $2 AND timestamp > $3"
        EXISTS_MSGS_TABLE=          "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'MESSAGES');"


    ### ============================== GALLARY MESSAGES TABLE ==============================
        CREATE_GALL_MSGS_TABLE =    """ 
                                    CREATE TABLE IF NOT EXISTS gallery_messages (
                                        msg_id BIGINT PRIMARY KEY,
                                        ch_id BIGINT NOT NULL,
                                        srv_id BIGINT NOT NULL,
                                        auth_id BIGINT,
                                        timestamp TIMESTAMP NOT NULL
                                        ); 
                                    """

        ADD_GALL_MSG=               """ 
                                    INSERT INTO gallery_messages(
                                        msg_id, 
                                        ch_id, 
                                        guild_id,
                                        auth_id, 
                                        timestamp)
                                    VALUES( CAST($1 AS BIGINT), 
                                            CAST($2 AS BIGINT), 
                                            CAST($3 AS BIGINT), 
                                            CAST($4 AS BIGINT), 
                                            $5)
                                    ON CONFLICT (msg_id)
                                        DO NOTHING;
                                    """

        GET_GALL_MSG_AFTER=         "SELECT * FROM gallery_messages WHERE timestamp > $1"
        GET_GALL_MSG_BEFORE=         "SELECT * FROM gallery_messages WHERE timestamp < $1"
        GET_GALL_MSG_MEM_AFTER=     "SELECT * FROM gallery_messages WHERE auth_id = CAST($1 AS BIGINT) AND timestamp > $2"
        GET_GALL_CHIDS_AFTER=       'SELECT DISTINCT ch_id FROM public.gallery_messages WHERE timestamp > $1'
        GET_GALL_CHIDS_BEFORE=      'SELECT DISTINCT ch_id FROM public.gallery_messages WHERE timestamp < $1'
        EXISTS_GALL_MSGS_TABLE=     "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'GALLERY_MESSAGES');"
        DEL_GALL_MSGS_FROM_CH=      "DELETE FROM gallery_messages WHERE ch_id = CAST($1 AS BIGINT) AND guild_id = CAST($2 AS BIGINT);"
        DEL_GALL_MSGS_BEFORE=       "DELETE FROM public.gallery_messages WHERE guild_id = CAST($1 AS BIGINT) AND timestamp < $2;"


    ### ============================== MEMBERS TABLE ==============================
        CREATE_MEMBERS_TABLE =      """ CREATE TABLE IF NOT EXISTS members (
                                            num BIGSERIAL PRIMARY KEY,
                                            user_id BIGINT NOT NULL,
                                            joindate TIMESTAMP,
                                            creationdate TIMESTAMP,
                                            ishere BOOLEAN DEFAULT TRUE,
                                            nummsgs BIGINT DEFAULT 0,
                                            gems BIGINT DEFAULT 0,
                                            level SMALLINT DEFAULT 0,
                                            bonus TEXT DEFAULT '',
                                            CONSTRAINT mem_unique UNIQUE (user_id)
                                            ); 
                                    """
        add_a_member=               """ 
                                        INSERT INTO members(
                                                user_id,
                                                joindate,
                                                creationdate,
                                                ishere)
                                        VALUES( CAST($1 AS BIGINT), 
                                                $2,
                                                $3,
                                                $4
                                                );
                                    """
        ADD_MEMBER_FUNC=            """ 
                                        INSERT INTO members(
                                                user_id,
                                                joindate,
                                                creationdate) 
                                        VALUES( CAST($1 AS BIGINT), 
                                                $2,
                                                $3
                                                )
                                        ON CONFLICT (user_id)
                                            DO
                                                UPDATE SET ishere = TRUE;
                                    """
        readd_a_member=             "UPDATE members SET ishere = TRUE WHERE user_id = $1;"
        remove_a_member=            "DELETE FROM members WHERE user_id = CAST($1 AS BIGINT)"
        REMOVE_MEMBER_FUNC=         "UPDATE members SET ishere = FALSE WHERE user_id = $1;"
        get_all_members=            "SELECT FROM members"
        get_all_members_id=         "SELECT user_id FROM members"
        get_all_members_joinleave=  "SELECT user_id, ishere FROM members"
        get_member_id=              "SELECT * FROM members WHERE user_id = CAST($1 AS BIGINT)"
        get_member_leaderboard =    "SELECT * FROM members WHERE ishere = TRUE ORDER BY nummsgs DESC LIMIT 10;"
        member_table_empty_test=    "SELECT * FROM members ORDER BY num ASC LIMIT 1"
        EXISTS_MEMBERS_TABLE=       "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'MEMBERS');"


    ### ============================== INVITE TABLE ==============================
        CREATE_INVITE_TABLE=        """ 
                                    CREATE TABLE IF NOT EXISTS invites (data jsonb PRIMARY KEY);
                                    """

        ADD_INVITES=                """ 
                                    SELECT updatestoredinvites($1)
                                    """

        GET_INVITE_DATA=            """
                                    SELECT * FROM invites
                                    """

        DELETE_INVITE_DATA=         """ 
                                    TRUNCATE invites; 
                                    DELETE FROM invites;
                                    """

        EXISTS_INVITE_TABLE=        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'INVITES');"


    ### ============================== ARTIST INFO TABLE ==============================
        CREATE_ARTIST_INFO_TABLE =  """ CREATE TABLE IF NOT EXISTS artist_info (
                                            user_id BIGINT PRIMARY KEY,
                                            info TEXT DEFAULT 'Artist provided no info.'
                                            );
                                    """
        add_to_artist_info_table =  """ INSERT INTO artist_info(
                                            user_id, 
                                            info) 
                                        VALUES( CAST($1 AS BIGINT), 
                                                $2)
                                    """
        remove_from_artist_info_table = "DELETE FROM artist_info WHERE user_id = CAST($1 AS BIGINT)"
        GET_ALL_ARTIST_INFO=            "SELECT * FROM artist_info"
        UPDATE_ARTIST_INFO=             "SELECT updateartistInfo(CAST($1 AS BIGINT), $2)"

        EXISTS_ARTIST_INFO_TABLE=    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'ARTIST_INFO');"

                           
    ### ============================== WELCOME MESSAGE TABLE ==============================
        CREATE_WEL_MSG_TABLE=       """ 
                                    CREATE TABLE IF NOT EXISTS welcome_msg (
                                        msg_id BIGINT PRIMARY KEY,
                                        ch_id BIGINT NOT NULL,
                                        srv_id BIGINT NOT NULL,
                                        user_id BIGINT NOT NULL
                                        );
                                    """
        ADD_WEL_MSG=                """ 
                                    INSERT INTO welcome_msg (
                                        msg_id,
                                        ch_id,
                                        srv_id,
                                        user_id)
                                    VALUES( CAST($1 AS BIGINT),
                                            CAST($2 AS BIGINT), 
                                            CAST($3 AS BIGINT), 
                                            CAST($4 AS BIGINT))
                                    """

        REM_MEM_WEL_MSG=            "DELETE FROM welcome_msg WHERE user_id = $1"
        GET_MEM_WEL_MSG=            "SELECT * FROM welcome_msg WHERE user_id = $1"
        GET_ALL_WEL_MSG=            "SELECT * FROM welcome_msg"
        EXISTS_WEL_MSG_TABLE=       "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'WELCOME_MSG');"

        
    ### ============================== REACTION MESSAGE TABLE ==============================
        CREATE_RECT_MSG_TABLE=      """
                                    CREATE TABLE IF NOT EXISTS reaction_messages (
                                        msg_id BIGINT PRIMARY KEY,
                                        ch_id BIGINT NOT NULL,
                                        srv_id BIGINT NOT NULL,
                                        function_name VARCHAR(50) NOT NULL,
                                        emojikey JSONB NOT NULL,
                                        num BIGSERIAL
                                        ); 
                                    """

        ADD_RECT_MSG=               """
                                    INSERT INTO reaction_messages (
                                        msg_id,
                                        ch_id,
                                        srv_id,
                                        function_name,
                                        emojikey)
                                    VALUES( CAST($1 AS BIGINT),
                                            CAST($2 AS BIGINT), 
                                            CAST($3 AS BIGINT), 
                                            $4,
                                            $5)
                                    ON CONFLICT (msg_id)
                                        DO NOTHING;
                                    """


        GET_RECT_MSG_MSGID=         "SELECT * FROM reaction_messages WHERE msg_id = $1"
        EXISTS_RECT_MSG_TABLE=      "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'REACTION_MESSAGES');"


    ### ============================== GIVEAWAY WINNERS TABLE ==============================
        CREATE_GVWY_PRE_WINS_TABLE= """
                                    CREATE TABLE IF NOT EXISTS gvwy_previous_wins(
                                        user_id bigint PRIMARY KEY,
                                        first_win TIMESTAMP,
                                        last_win TIMESTAMP,
                                        num_wins INTEGER
                                        ); 
                                    """

        ADD_GVWY_PRE_WINS=          """
                                    INSERT INTO gvwy_previous_wins(
                                            user_id,
                                            first_win,
                                            last_win,
                                            num_wins
                                            ) 
                                    VALUES( CAST($1 AS BIGINT), 
                                            $2,
                                            $2,
                                            1
                                            )

                                    ON CONFLICT (user_id)
                                        DO
                                            UPDATE
                                                SET num_wins = gvwy_previous_wins.num_wins + 1,
                                                    last_win = $2
                                                WHERE gvwy_previous_wins.user_id = CAST($1 AS BIGINT);
                                    """
        GET_ALL_GVWY_PRE_WINS=      "SELECT * FROM gvwy_previous_wins"
        GET_GVWY_NUM_WINS=          "SELECT num_wins FROM gvwy_previous_wins WHERE user_id = CAST($1 AS BIGINT)"
        GET_MEM_EXISTS_GVWY_PRE_WINS="SELECT EXISTS(SELECT * FROM gvwy_previous_wins WHERE user_id = CAST($1 AS BIGINT))"
        GET_MEM_GVWY_PRE_WIN=       "SELECT * FROM gvwy_previous_wins WHERE user_id = CAST($1 AS BIGINT);"
        SET_GVWY_NUM_WINS=          "UPDATE gvwy_previous_wins SET num_wins = CAST($1 AS INTEGER) WHERE gvwy_previous_wins.user_id = CAST($2 AS BIGINT);"
        REM_MEM_GVWY_PRE_WINS=      "DELETE FROM gvwy_previous_wins WHERE user_id = CAST($1 AS BIGINT)"
        EXISTS_GVWY_PRE_WINS_TABLE= "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'GVWY_PREVIOUS_WINS');"


    ### ============================== GIVEAWAY BLOCKS TABLE ==============================    
        CREATE_GVWY_BLOCKS_TABLE=   """
                                    CREATE TABLE IF NOT EXISTS gvwy_blocks(
                                        user_id BIGINT PRIMARY KEY,
                                        blocked_by BIGINT,
                                        reason VARCHAR(1000),
                                        timestamp TIMESTAMP,
                                        timed BOOLEAN DEFAULT FALSE,
                                        unblock_timestamp TIMESTAMP
                                        );
                                    """
        ADD_GVWY_BLOCKS_NONTIMED=   """
                                    INSERT INTO gvwy_blocks(
                                            user_id,
                                            blocked_by,
                                            reason,
                                            timestamp
                                            )
                                    VALUES(
                                            CAST($1 AS BIGINT),
                                            CAST($2 AS BIGINT),
                                            $3,
                                            $4
                                            )

                                    ON CONFLICT (user_id)
                                        DO NOTHING;
                                    """
        ADD_GVWY_BLOCKS=            """
                                    INSERT INTO gvwy_blocks(
                                            user_id,
                                            blocked_by,
                                            reason,
                                            timestamp,
                                            timed,
                                            unblock_timestamp
                                            )
                                    VALUES(
                                            CAST($1 AS BIGINT),
                                            CAST($2 AS BIGINT),
                                            $3,
                                            $4,
                                            $5,
                                            $6
                                            )

                                    ON CONFLICT (user_id)
                                        DO NOTHING;
                                    """
        
        GET_ALL_GVWY_BLOCKS=        "SELECT * FROM gvwy_blocks"
        GET_MEM_GVWY_BLOCKS=        "SELECT * FROM gvwy_blocks WHERE user_id = CAST($1 AS BIGINT)"
        GET_MEM_EXISTS_GVWY_BLOCKS= "SELECT EXISTS(SELECT * FROM gvwy_blocks WHERE user_id = CAST($1 AS BIGINT))"
        REM_MEM_GVWY_BLOCK=         "DELETE FROM gvwy_blocks WHERE user_id = CAST($1 AS BIGINT)"
        
        EXISTS_GVWY_BLOCKS_TABLE=   "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'GVWY_BLOCKS');"
    

    ### ============================== GIVEAWAY ENTRIES TABLE ==============================
      
        CREATE_GVWY_ENTRIES_TABLE=  """
                                    CREATE TABLE IF NOT EXISTS gvwy_entries(
                                        user_id BIGINT PRIMARY KEY,
										entries SMALLINT DEFAULT 3,
										timestamp TIMESTAMP
                                    ); 
                                    """
        ADD_GVWY_ENTRY=             """
                                    INSERT INTO gvwy_entries(
                                        user_id,
                                        entries,
                                        timestamp
                                        )
                                    VALUES(
                                        CAST($1 AS BIGINT),
                                        CAST($2 AS SMALLINT),
                                        $3
                                        )
                                    ON CONFLICT(user_id)
                                        DO NOTHING;
                                    """
        GET_ALL_GVWY_ENTRIES=       "SELECT * FROM gvwy_entries ORDER BY timestamp ASC"
        GET_MEM_GVWY_ENTRIES=       "SELECT * FROM gvwy_entries WHERE user_id=CAST($1 AS BIGINT)"
        GET_MEM_EXISTS_GVWY_ENTRIES="SELECT EXISTS(SELECT * FROM gvwy_entries WHERE user_id=CAST($1 AS BIGINT))"
        REM_MEM_GVWY_ENTRIES=       "DELETE FROM gvwy_entries WHERE user_id = CAST($1 AS BIGINT)"
        REM_ALL_GVWY_ENTRIES=       """ 
                                    TRUNCATE gvwy_entries; 
                                    DELETE FROM gvwy_entries;
                                    """
        EXISTS_GVWY_ENTRIES_TABLE=  "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'GVWY_ENTRIES');"


    ### ============================== DM FEEDBACK TABLE ==============================
        CREATE_DM_FEEDBACK=     """
                                CREATE TABLE IF NOT EXISTS dm_feedback (
                                    num SERIAL PRIMARY KEY,
                                    user_id BIGINT, 
                                    dmchannel_id BIGINT, 
                                    sent_msg_id BIGINT, 
                                    sent_chl_id BIGINT,
                                    sent_srv_id BIGINT,
                                    timestamp TIMESTAMP
                                    );
                                """

        ADD_DM_FEEDBACK=        """
                                INSERT INTO dm_feedback(
                                    user_id,
                                    dmchannel_id,
                                    sent_msg_id,
                                    sent_chl_id,
                                    sent_srv_id,
                                    timestamp
                                    )

                                VALUES(
                                    CAST($1 AS BIGINT),
                                    CAST($2 AS BIGINT),
                                    CAST($3 AS BIGINT),
                                    CAST($4 AS BIGINT),
                                    CAST($5 AS BIGINT),
                                    $6
                                    )
                                    
                                ON CONFLICT(num)
                                    DO NOTHING;
                                """

        GET_MEM_DM_FEEDBACK=    "SELECT * FROM dm_feedback WHERE sent_msg_id = CAST($1 AS BIGINT) AND sent_srv_id = CAST($2 AS BIGINT)"
        GET_MEM_CH_DM_FEEDBACK= "SELECT * FROM dm_feedback WHERE sent_msg_id = CAST($1 AS BIGINT) AND sent_chl_id = CAST($2 AS BIGINT) AND sent_srv_id = CAST($3 AS BIGINT)"
        EXISTS_DM_FEEDBACK=     "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'DM_FEEDBACK');"


    ### ============================== GUILD TABLE ==============================
        CREATE_GUILD =          """ 
                                CREATE TABLE IF NOT EXISTS guild (
                                    guild_id        BIGINT          PRIMARY KEY,
                                    owner_id        BIGINT          NOT NULL,
                                    creation_date   TIMESTAMP       DEFAULT (NOW() at time zone 'utc'),
                                    hstaff_r        BIGINT          DEFAULT 0,
                                    lstaff_r        BIGINT          DEFAULT 0,
                                    owner_hist      BIGINT[]        DEFAULT ARRAY[282293589713616896]::BIGINT[],
                                    hstaff_hist     BIGINT[]        DEFAULT ARRAY[]::BIGINT[],
                                    lstaff_hist     BIGINT[]        DEFAULT ARRAY[]::BIGINT[],
                                    roles           BIGINT[]        DEFAULT ARRAY[]::BIGINT[],
                                    channels        BIGINT[]        DEFAULT ARRAY[]::BIGINT[],
                                    active_bans     DISCORD_BAN[],
                                    unban_hist      DISCORD_BAN[],
                                    emojis          DISCORD_EMOJI[],
                                    gall_nbl        BOOLEAN         DEFAULT FALSE,
                                    gall_ch         BIGINT[]        DEFAULT ARRAY[]::BIGINT[],
                                    gall_text_exp   INTEGER,
                                    gall_user_wl    BIGINT[],       DEFAULT ARRAY[]::BIGINT[],
                                    gall_nbl_links  BOOLEAN         DEFAULT FALSE,
                                    gall_links      VARCHAR(80)[]
                                );
                                """

        EXISTS_GUILD=           "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'GUILD');"

        GET_GUILD_GALL_CONFIG=  "SELECT guild_id, gall_nbl, gall_ch, gall_text_exp, gall_user_wl, gall_nbl_links, gall_links FROM guild;"
        SET_GUILD_GALL_CONFIG=  """
                                UPDATE guild 
                                SET 
                                    gall_nbl = CAST($1 AS BOOLEAN),
                                    gall_ch = CAST($2 AS BIGINT[]),
                                    gall_text_exp = CAST($3 AS INTEGER),
                                    gall_user_wl = CAST($4 AS BIGINT[]),
                                    gall_nbl_links = CAST($5 AS BOOLEAN),
                                    gall_links = CAST($6 AS VARCHAR(80)[])

                                WHERE 
                                    guild.guild_id = CAST($7 AS BIGINT);
                                """
        SET_GUILD_GALL_ENABLE=      "UPDATE guild SET gall_nbl = TRUE WHERE guild.guild_id = CAST($1 AS BIGINT);"
        SET_GUILD_GALL_DISABLE=     "UPDATE guild SET gall_nbl = FALSE WHERE guild.guild_id = CAST($1 AS BIGINT);"
        SET_GUILD_GALL_CHLS=        "UPDATE guild SET gall_ch = CAST($1 AS BIGINT[]) WHERE guild.guild_id = CAST($2 AS BIGINT);"
        SET_GUILD_GALL_EXP=         "UPDATE guild SET gall_text_exp = CAST($1 AS INTEGER) WHERE guild.guild_id = CAST($2 AS BIGINT);"
        SET_GUILD_GALL_USER_WL=     "UPDATE guild SET gall_user_wl = CAST($1 AS BIGINT[]) WHERE guild.guild_id = CAST($2 AS BIGINT);"
        SET_GUILD_GALL_LINK_ENABLE= "UPDATE guild SET gall_nbl_links = TRUE WHERE guild.guild_id = CAST($1 AS BIGINT);"
        SET_GUILD_GALL_LINK_DISABLE="UPDATE guild SET gall_nbl_links = FALSE WHERE guild.guild_id = CAST($1 AS BIGINT);"
        SET_GUILD_GALL_LINKS=       "UPDATE guild SET gall_links = CAST($1 AS BIGINT[]) WHERE guild.guild_id = CAST($2 AS BIGINT);"

                                            


    ### ============================== TRIGGERS ==============================
        CREATE_MSGINCREMENTER=      """
                                    DO
                                    $do$
                                    BEGIN
                                    IF NOT EXISTS(	SELECT *
                                            FROM pg_proc
                                            WHERE prorettype <> 0 AND proname = 'incrementusermsgcounter' AND format_type(prorettype, NULL) = 'trigger') THEN

                                        CREATE OR REPLACE FUNCTION incrementUserMSGCounter() RETURNS trigger
                                            LANGUAGE plpgsql
                                            cost 200 AS
                                        $$BEGIN
                                            UPDATE members SET nummsgs = (nummsgs +1) WHERE user_id = NEW.auth_id;
                                            RETURN NEW;
                                        END;$$;
                                    END IF;

                                    IF NOT EXISTS(SELECT * FROM information_schema.triggers WHERE event_object_table = 'messages' AND trigger_name = 'msgincrementer') THEN
                                        CREATE TRIGGER msgIncrementer BEFORE INSERT ON messages FOR EACH ROW
                                            EXECUTE PROCEDURE incrementUserMSGCounter();
                                    END IF;
                                    END
                                    $do$
                                    """
        EXISTS_MSGINCREMENTER=      "SELECT EXISTS(SELECT * FROM information_schema.triggers WHERE upper(trigger_name) = 'MSGINCREMENTER');"

    ### ============================== FUNCTIONS ==============================
        
        # -------------------- UPDATE_INVITES --------------------
        CREATE_FUNC_UPDATE_INVITES= """
                                    DO
                                    $do$
                                    BEGIN
                                    IF NOT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'updatestoredinvites') THEN

                                        CREATE FUNCTION updatestoredinvites(u JSONB) 
                                        RETURNS void AS
                                        '   
                                        BEGIN
                                            IF EXISTS (select * from invites LIMIT 1) THEN
                                                TRUNCATE invites; 
                                                DELETE FROM invites;

                                                INSERT INTO invites VALUES (u);
                                            ELSE 
                                                INSERT INTO invites VALUES (u);
                                            END IF;
                                        END;
                                        '
                                        LANGUAGE plpgsql
                                        COST 200;

                                    END IF;
                                    END
                                    $do$
                                    """

        EXISTS_FUNC_UPDATE_INVITES= "SELECT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'updatestoredinvites')"

        # -------------------- HAS_MEMBER_LEVELED_UP --------------------
        CREATE_FUNC_HAS_MEMBER_LEVELED_UP=  """
                                            DO
                                            $do$
                                            BEGIN
                                            IF NOT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'hasmemberleveledup') THEN 
                                                CREATE FUNCTION hasMemberLeveledUp(u BIGINT) 
                                                RETURNS TABLE (
                                                    new_level SMALLINT,
                                                    has_leveled_up BOOLEAN
                                                ) AS
                                                '
                                                DECLARE
                                                new_level SMALLINT;
                                                old_level SMALLINT := (	SELECT level
                                                        FROM members 
                                                        WHERE user_id = u);
                                                new_nummsgs BIGINT := (	SELECT nummsgs
                                                        FROM members 
                                                        WHERE user_id = u);
                                                leveled_up BOOLEAN := 	FALSE;

                                                BEGIN
                                                    CASE 
                                                    WHEN new_nummsgs >= 0 AND new_nummsgs < 10 THEN new_level = 0;
                                                    WHEN new_nummsgs >= 10 AND new_nummsgs < 75 THEN new_level = 1;
                                                    WHEN new_nummsgs >= 75 AND new_nummsgs < 200 THEN new_level = 2;
                                                    WHEN new_nummsgs >= 200 AND new_nummsgs < 500 THEN new_level = 3;
                                                    WHEN new_nummsgs >= 500 AND new_nummsgs < 575 THEN new_level = 4;
                                                    WHEN new_nummsgs >= 500 AND new_nummsgs < 575 THEN new_level = 5;
                                                    WHEN new_nummsgs >= 575 AND new_nummsgs < 661 THEN new_level = 6;
                                                    WHEN new_nummsgs >= 661 AND new_nummsgs < 760 THEN new_level = 7;
                                                    WHEN new_nummsgs >= 760 AND new_nummsgs < 874 THEN new_level = 8;
                                                    WHEN new_nummsgs >= 874 AND new_nummsgs < 1005 THEN new_level = 9;
                                                    WHEN new_nummsgs >= 1005 AND new_nummsgs < 1156 THEN new_level = 10;
                                                    WHEN new_nummsgs >= 1156 AND new_nummsgs < 1318 THEN new_level = 11;
                                                    WHEN new_nummsgs >= 1318 AND new_nummsgs < 1503 THEN new_level = 12;
                                                    WHEN new_nummsgs >= 1503 AND new_nummsgs < 1713 THEN new_level = 13;
                                                    WHEN new_nummsgs >= 1713 AND new_nummsgs < 1953 THEN new_level = 14;
                                                    WHEN new_nummsgs >= 1953 AND new_nummsgs < 2226 THEN new_level = 15;
                                                    WHEN new_nummsgs >= 2226 AND new_nummsgs < 2538 THEN new_level = 16;
                                                    WHEN new_nummsgs >= 2538 AND new_nummsgs < 2893 THEN new_level = 17;
                                                    WHEN new_nummsgs >= 2893 AND new_nummsgs < 3298 THEN new_level = 18;
                                                    WHEN new_nummsgs >= 3298 AND new_nummsgs < 3760 THEN new_level = 19;
                                                    WHEN new_nummsgs >= 3760 AND new_nummsgs < 4286 THEN new_level = 20;
                                                    WHEN new_nummsgs >= 4286 AND new_nummsgs < 4843 THEN new_level = 21;
                                                    WHEN new_nummsgs >= 4843 AND new_nummsgs < 5473 THEN new_level = 22;
                                                    WHEN new_nummsgs >= 5473 AND new_nummsgs < 6184 THEN new_level = 23;
                                                    WHEN new_nummsgs >= 6184 AND new_nummsgs < 6988 THEN new_level = 24;
                                                    WHEN new_nummsgs >= 6988 AND new_nummsgs < 7896 THEN new_level = 25;
                                                    WHEN new_nummsgs >= 7896 AND new_nummsgs < 8922 THEN new_level = 26;
                                                    WHEN new_nummsgs >= 8922 AND new_nummsgs < 10082 THEN new_level = 27;
                                                    WHEN new_nummsgs >= 10082 AND new_nummsgs < 11393 THEN new_level = 28;
                                                    WHEN new_nummsgs >= 11393 AND new_nummsgs < 12874 THEN new_level = 29;
                                                    WHEN new_nummsgs >= 12874 AND new_nummsgs < 14548 THEN new_level = 30;
                                                    WHEN new_nummsgs >= 14548 AND new_nummsgs < 16294 THEN new_level = 31;
                                                    WHEN new_nummsgs >= 16294 AND new_nummsgs < 18249 THEN new_level = 32;
                                                    WHEN new_nummsgs >= 18249 AND new_nummsgs < 20439 THEN new_level = 33;
                                                    WHEN new_nummsgs >= 20439 AND new_nummsgs < 22892 THEN new_level = 34;
                                                    WHEN new_nummsgs >= 22892 AND new_nummsgs < 25639 THEN new_level = 35;
                                                    WHEN new_nummsgs >= 25639 AND new_nummsgs < 28716 THEN new_level = 36;
                                                    WHEN new_nummsgs >= 28716 AND new_nummsgs < 32162 THEN new_level = 37;
                                                    WHEN new_nummsgs >= 32162 AND new_nummsgs < 36021 THEN new_level = 38;
                                                    WHEN new_nummsgs >= 36021 AND new_nummsgs < 40344 THEN new_level = 39;
                                                    WHEN new_nummsgs >= 40344 AND new_nummsgs < 45185 THEN new_level = 40;
                                                    WHEN new_nummsgs >= 45185 AND new_nummsgs < 50155 THEN new_level = 41;
                                                    WHEN new_nummsgs >= 50155 AND new_nummsgs < 55672 THEN new_level = 42;
                                                    WHEN new_nummsgs >= 55672 AND new_nummsgs < 61796 THEN new_level = 43;
                                                    WHEN new_nummsgs >= 61796 AND new_nummsgs < 68594 THEN new_level = 44;
                                                    WHEN new_nummsgs >= 68594 AND new_nummsgs < 76139 THEN new_level = 45;
                                                    WHEN new_nummsgs >= 76139 AND new_nummsgs < 84514 THEN new_level = 46;
                                                    WHEN new_nummsgs >= 84514 AND new_nummsgs < 93811 THEN new_level = 47;
                                                    WHEN new_nummsgs >= 93811 AND new_nummsgs < 104130 THEN new_level = 48;
                                                    WHEN new_nummsgs >= 104130 AND new_nummsgs < 115584 THEN new_level = 49;
                                                    WHEN new_nummsgs >= 115584 AND new_nummsgs < 128298 THEN new_level = 50;
                                                    WHEN new_nummsgs >= 128298 AND new_nummsgs < 141769 THEN new_level = 51;
                                                    WHEN new_nummsgs >= 141769 AND new_nummsgs < 156655 THEN new_level = 52;
                                                    WHEN new_nummsgs >= 156655 AND new_nummsgs < 173104 THEN new_level = 53;
                                                    WHEN new_nummsgs >= 173104 AND new_nummsgs < 191280 THEN new_level = 54;
                                                    WHEN new_nummsgs >= 191280 AND new_nummsgs < 211364 THEN new_level = 55;
                                                    WHEN new_nummsgs >= 211364 AND new_nummsgs < 233557 THEN new_level = 56;
                                                    WHEN new_nummsgs >= 233557 AND new_nummsgs < 258080 THEN new_level = 57;
                                                    WHEN new_nummsgs >= 258080 AND new_nummsgs < 285178 THEN new_level = 58;
                                                    WHEN new_nummsgs >= 285178 AND new_nummsgs < 315122 THEN new_level = 59;
                                                    WHEN new_nummsgs >= 315122 AND new_nummsgs < 348210 THEN new_level = 60;
                                                    WHEN new_nummsgs >= 348210 AND new_nummsgs < 383031 THEN new_level = 61;
                                                    WHEN new_nummsgs >= 383031 AND new_nummsgs < 421334 THEN new_level = 62;
                                                    WHEN new_nummsgs >= 421334 AND new_nummsgs < 463467 THEN new_level = 63;
                                                    WHEN new_nummsgs >= 463467 AND new_nummsgs < 509814 THEN new_level = 64;
                                                    WHEN new_nummsgs >= 509814 AND new_nummsgs < 560795 THEN new_level = 65;
                                                    WHEN new_nummsgs >= 560795 AND new_nummsgs < 616874 THEN new_level = 66;
                                                    WHEN new_nummsgs >= 616874 AND new_nummsgs < 678561 THEN new_level = 67;
                                                    WHEN new_nummsgs >= 678561 AND new_nummsgs < 746417 THEN new_level = 68;
                                                    WHEN new_nummsgs >= 746417 AND new_nummsgs < 821059 THEN new_level = 69;
                                                    WHEN new_nummsgs >= 821059 AND new_nummsgs < 903165 THEN new_level = 70;
                                                    WHEN new_nummsgs >= 903165 AND new_nummsgs < 988966 THEN new_level = 71;
                                                    WHEN new_nummsgs >= 988966 AND new_nummsgs < 1082918 THEN new_level = 72;
                                                    WHEN new_nummsgs >= 1082918 AND new_nummsgs < 1185795 THEN new_level = 73;
                                                    WHEN new_nummsgs >= 1185795 AND new_nummsgs < 1298446 THEN new_level = 74;
                                                    WHEN new_nummsgs >= 1298446 AND new_nummsgs < 1421798 THEN new_level = 75;
                                                    WHEN new_nummsgs >= 1421798 AND new_nummsgs < 1556869 THEN new_level = 76;
                                                    WHEN new_nummsgs >= 1556869 AND new_nummsgs < 1704772 THEN new_level = 77;
                                                    WHEN new_nummsgs >= 1704772 AND new_nummsgs < 1866725 THEN new_level = 78;
                                                    WHEN new_nummsgs >= 1866725 AND new_nummsgs < 2044064 THEN new_level = 79;
                                                    WHEN new_nummsgs >= 2044064 AND new_nummsgs < 2238250 THEN new_level = 80;
                                                    WHEN new_nummsgs >= 2238250 AND new_nummsgs < 2439692 THEN new_level = 81;
                                                    WHEN new_nummsgs >= 2439692 AND new_nummsgs < 2659264 THEN new_level = 82;
                                                    WHEN new_nummsgs >= 2659264 AND new_nummsgs < 2898598 THEN new_level = 83;
                                                    WHEN new_nummsgs >= 2898598 AND new_nummsgs < 3159472 THEN new_level = 84;
                                                    WHEN new_nummsgs >= 3159472 AND new_nummsgs < 3443824 THEN new_level = 85;
                                                    WHEN new_nummsgs >= 3443824 AND new_nummsgs < 3753768 THEN new_level = 86;
                                                    WHEN new_nummsgs >= 3753768 AND new_nummsgs < 4091607 THEN new_level = 87;
                                                    WHEN new_nummsgs >= 4091607 AND new_nummsgs < 4459852 THEN new_level = 88;
                                                    WHEN new_nummsgs >= 4459852 AND new_nummsgs < 4861239 THEN new_level = 89;
                                                    WHEN new_nummsgs >= 4861239 AND new_nummsgs < 5298751 THEN new_level = 90;
                                                    WHEN new_nummsgs >= 5298751 AND new_nummsgs < 5749145 THEN new_level = 91;
                                                    WHEN new_nummsgs >= 5749145 AND new_nummsgs < 6237822 THEN new_level = 92;
                                                    WHEN new_nummsgs >= 6237822 AND new_nummsgs < 6768037 THEN new_level = 93;
                                                    WHEN new_nummsgs >= 6768037 AND new_nummsgs < 7343320 THEN new_level = 94;
                                                    WHEN new_nummsgs >= 7343320 AND new_nummsgs < 7967502 THEN new_level = 95;
                                                    WHEN new_nummsgs >= 7967502 AND new_nummsgs < 8644740 THEN new_level = 96;
                                                    WHEN new_nummsgs >= 8644740 AND new_nummsgs < 9379543 THEN new_level = 97;
                                                    WHEN new_nummsgs >= 9379543 AND new_nummsgs < 10176804 THEN new_level = 98;
                                                    WHEN new_nummsgs >= 10176804 AND new_nummsgs < 11041832 THEN new_level = 99;
                                                    ELSE new_level = 100;
                                                    END CASE;
                                                    
                                                    IF new_level > old_level THEN
                                                    leveled_up = TRUE;
                                                    END IF;

                                                    return QUERY SELECT new_level, leveled_up;
                                                END;
                                                '
                                                LANGUAGE plpgsql
                                                COST 200;
                                            END IF;
                                            END
                                            $do$
                                            """

        EXISTS_FUNC_HAS_MEMBER_LEVELED_UP= "SELECT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'hasmemberleveledup')"
        HAS_MEMBER_LEVELED_UP = "SELECT * FROM hasMemberLeveledUp(CAST($1 AS BIGINT))"
        MEMBER_LEVELED_UP = "UPDATE members SET level = CAST($1 AS INTEGER), gems = CAST($2 AS BIGINT) WHERE user_id = CAST($3 AS BIGINT)"

        # -------------------- GEMS --------------------

        CREATE_FUNC_MEMBER_LEVEL_REWARD=    """        
                                            DO
                                            $do$
                                            BEGIN
                                            IF NOT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'memberleveledupreward') THEN 

                                                CREATE FUNCTION memberLeveledUpReward(u BIGINT, level SMALLINT) 
                                                RETURNS TABLE (
                                                    reward BIGINT,
                                                    total BIGINT
                                                ) AS
                                                '
                                                DECLARE
                                                    reward BIGINT;
                                                    total BIGINT;
                                                    old_gems BIGINT := (SELECT gems FROM members WHERE user_id = u);

                                                BEGIN
                                                    CASE
                                                        WHEN level = 1 THEN reward = 50;
                                                        WHEN level = 2 THEN reward = 50;
                                                        WHEN level = 3 THEN reward = 50;
                                                        WHEN level = 4 THEN reward = 50;
                                                        WHEN level = 5 THEN reward = 60;
                                                        WHEN level = 6 THEN reward = 60;
                                                        WHEN level = 7 THEN reward = 60;
                                                        WHEN level = 8 THEN reward = 60;
                                                        WHEN level = 9 THEN reward = 60;
                                                        WHEN level = 10 THEN reward = 78;
                                                        WHEN level = 11 THEN reward = 78;
                                                        WHEN level = 12 THEN reward = 78;
                                                        WHEN level = 13 THEN reward = 78;
                                                        WHEN level = 14 THEN reward = 78;
                                                        WHEN level = 15 THEN reward = 94;
                                                        WHEN level = 16 THEN reward = 94;
                                                        WHEN level = 17 THEN reward = 94;
                                                        WHEN level = 18 THEN reward = 94;
                                                        WHEN level = 19 THEN reward = 94;
                                                        WHEN level = 20 THEN reward = 122;
                                                        WHEN level = 21 THEN reward = 122;
                                                        WHEN level = 22 THEN reward = 122;
                                                        WHEN level = 23 THEN reward = 122;
                                                        WHEN level = 24 THEN reward = 122;
                                                        WHEN level = 25 THEN reward = 146;
                                                        WHEN level = 26 THEN reward = 146;
                                                        WHEN level = 27 THEN reward = 146;
                                                        WHEN level = 28 THEN reward = 146;
                                                        WHEN level = 29 THEN reward = 146;
                                                        WHEN level = 30 THEN reward = 190;
                                                        WHEN level = 31 THEN reward = 190;
                                                        WHEN level = 32 THEN reward = 190;
                                                        WHEN level = 33 THEN reward = 190;
                                                        WHEN level = 34 THEN reward = 190;
                                                        WHEN level = 35 THEN reward = 228;
                                                        WHEN level = 36 THEN reward = 228;
                                                        WHEN level = 37 THEN reward = 228;
                                                        WHEN level = 38 THEN reward = 228;
                                                        WHEN level = 39 THEN reward = 228;
                                                        WHEN level = 40 THEN reward = 296;
                                                        WHEN level = 41 THEN reward = 296;
                                                        WHEN level = 42 THEN reward = 296;
                                                        WHEN level = 43 THEN reward = 296;
                                                        WHEN level = 44 THEN reward = 296;
                                                        WHEN level = 45 THEN reward = 355;
                                                        WHEN level = 46 THEN reward = 355;
                                                        WHEN level = 47 THEN reward = 355;
                                                        WHEN level = 48 THEN reward = 355;
                                                        WHEN level = 49 THEN reward = 355;
                                                        WHEN level = 50 THEN reward = 462;
                                                        WHEN level = 51 THEN reward = 462;
                                                        WHEN level = 52 THEN reward = 462;
                                                        WHEN level = 53 THEN reward = 462;
                                                        WHEN level = 54 THEN reward = 462;
                                                        WHEN level = 55 THEN reward = 554;
                                                        WHEN level = 56 THEN reward = 554;
                                                        WHEN level = 57 THEN reward = 554;
                                                        WHEN level = 58 THEN reward = 554;
                                                        WHEN level = 59 THEN reward = 554;
                                                        WHEN level = 60 THEN reward = 720;
                                                        WHEN level = 61 THEN reward = 720;
                                                        WHEN level = 62 THEN reward = 720;
                                                        WHEN level = 63 THEN reward = 720;
                                                        WHEN level = 64 THEN reward = 720;
                                                        WHEN level = 65 THEN reward = 864;
                                                        WHEN level = 66 THEN reward = 864;
                                                        WHEN level = 67 THEN reward = 864;
                                                        WHEN level = 68 THEN reward = 864;
                                                        WHEN level = 69 THEN reward = 864;
                                                        WHEN level = 70 THEN reward = 1123;
                                                        WHEN level = 71 THEN reward = 1123;
                                                        WHEN level = 72 THEN reward = 1123;
                                                        WHEN level = 73 THEN reward = 1123;
                                                        WHEN level = 74 THEN reward = 1123;
                                                        WHEN level = 75 THEN reward = 1348;
                                                        WHEN level = 76 THEN reward = 1348;
                                                        WHEN level = 77 THEN reward = 1348;
                                                        WHEN level = 78 THEN reward = 1348;
                                                        WHEN level = 79 THEN reward = 1348;
                                                        WHEN level = 80 THEN reward = 1752;
                                                        WHEN level = 81 THEN reward = 1752;
                                                        WHEN level = 82 THEN reward = 1752;
                                                        WHEN level = 83 THEN reward = 1752;
                                                        WHEN level = 84 THEN reward = 1752;
                                                        WHEN level = 85 THEN reward = 2102;
                                                        WHEN level = 86 THEN reward = 2102;
                                                        WHEN level = 87 THEN reward = 2102;
                                                        WHEN level = 88 THEN reward = 2102;
                                                        WHEN level = 89 THEN reward = 2102;
                                                        WHEN level = 90 THEN reward = 2733;
                                                        WHEN level = 91 THEN reward = 2733;
                                                        WHEN level = 92 THEN reward = 2733;
                                                        WHEN level = 93 THEN reward = 2733;
                                                        WHEN level = 94 THEN reward = 2733;
                                                        WHEN level = 95 THEN reward = 3280;
                                                        WHEN level = 96 THEN reward = 3280;
                                                        WHEN level = 97 THEN reward = 3280;
                                                        WHEN level = 98 THEN reward = 3280;
                                                        WHEN level = 99 THEN reward = 3280;
                                                        WHEN level = 100 THEN reward = 4264;
                                                        ELSE reward = 9999;
                                                    END CASE;

                                                    total = reward + old_gems;
                                                    return QUERY SELECT reward, total;

                                                END;
                                                '
                                                LANGUAGE plpgsql
                                                COST 200;
                                            END IF;
                                            END
                                            $do$
                                            """
        
        EXISTS_FUNC_MEMBER_LEVEL_REWARD=    "SELECT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'memberleveledupreward')"
        GET_LEVEL_UP_REWARD=                "SELECT * FROM memberLeveledUpReward(CAST($1 AS BIGINT), CAST($2 AS SMALLINT))"

        # -------------------- ARTIST_INFO --------------------
        CREATE_FUNC_ARTIST_INFO =  """  
                                    DO
                                    $do$
                                    BEGIN
                                    IF NOT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'updateartistinfo') THEN 
                                        CREATE FUNCTION updateArtistInfo(u BIGINT, i TEXT) 
                                        RETURNS void AS
                                            '	
                                            BEGIN
                                            INSERT INTO artist_info(
                                                        user_id, 
                                                        info) 
                                            VALUES( u, 
                                                i)
                                                
                                            ON CONFLICT (user_id)
                                                    DO
                                                UPDATE SET info = i;
                                            END;
                                        '
                                        LANGUAGE plpgsql
                                        COST 200;
                                        
                                    END IF;
                                    END
                                    $do$
                                    """

        EXISTS_FUNC_ARTIST_INFO=    "SELECT EXISTS(SELECT * FROM pg_proc WHERE prorettype <> 0 AND proname = 'updateartistinfo')"

    ### ============================== TEST STUFF ==============================
        #(emoji.id, emoji.ext, emoji.bytes, emoji.timestamp)
        discord_emoji=      """
                            DO $$
                            BEGIN
                                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'discord_emoji') THEN
                                    CREATE TYPE discord_emoji AS
                                    (
                                    field_1        BIGINT,
                                    field_2        VARCHAR(10),
                                    field_3        BYTEA,
                                    field_4		   TIMESTAMP
                                    );
                                END IF;
                            END$$;
                            """

        #(User banned, staff_id, Reason, timestamp)
        discord_bans=      """
                            DO $$
                            BEGIN
                                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'discord_ban') THEN
                                    CREATE TYPE discord_ban AS
                                    (
                                    field_1     BIGINT,
                                    field_2     BIGINT,
                                    field_3     VARCHAR(250),
                                    field_4     TIMESTAMP
                                    );
                                END IF;
                            END$$;
                            """


